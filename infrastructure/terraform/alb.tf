# Execution Market Infrastructure - Application Load Balancer

# ALB Security Group
resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-alb-sg"
  }
}

# ----------------------------------------------------------------------------
# Phase 3.3 — ALB access logs to S3
#
# Enables per-request access logs for forensics, abuse investigation, and
# compliance. Logs land in a dedicated private bucket with Glacier IR
# transition at 30 days and expiration at 365 days.
#
# The Elastic Load Balancing service account for us-east-2 (033677994240) is
# granted s3:PutObject on the prefix. See AWS docs:
#   https://docs.aws.amazon.com/elasticloadbalancing/latest/application/enable-access-logging.html
# ----------------------------------------------------------------------------

# AWS Elastic Load Balancing service account IDs per region.
# Used for the S3 bucket policy that permits ALB to write access logs.
locals {
  elb_account_ids = {
    "us-east-1"      = "127311923021"
    "us-east-2"      = "033677994240"
    "us-west-1"      = "027434742980"
    "us-west-2"      = "797873946194"
    "eu-west-1"      = "156460612806"
    "eu-west-2"      = "652711504416"
    "eu-central-1"   = "054676820928"
    "ap-southeast-1" = "114774131450"
    "ap-southeast-2" = "783225319266"
    "ap-northeast-1" = "582318560864"
  }
  alb_logs_bucket_name = lower("${local.name_prefix}-alb-access-logs-${local.region}-${substr(local.account_id, -6, 6)}")
}

resource "aws_s3_bucket" "alb_access_logs" {
  bucket        = local.alb_logs_bucket_name
  force_destroy = false

  tags = {
    Name    = "${local.name_prefix}-alb-access-logs"
    Purpose = "alb-access-logs"
  }
}

resource "aws_s3_bucket_public_access_block" "alb_access_logs" {
  bucket                  = aws_s3_bucket.alb_access_logs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "alb_access_logs" {
  bucket = aws_s3_bucket.alb_access_logs.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "alb_access_logs" {
  bucket = aws_s3_bucket.alb_access_logs.bucket

  rule {
    apply_server_side_encryption_by_default {
      # ALB access logs only support SSE-S3 (AES256), not SSE-KMS.
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_access_logs" {
  bucket = aws_s3_bucket.alb_access_logs.id

  rule {
    id     = "alb-logs-retention"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "GLACIER_IR"
    }

    expiration {
      days = 365
    }
  }
}

# Bucket policy granting the regional ALB service account PutObject on the
# log prefix. s3:GetBucketAcl is required by the ELB control plane to verify
# the bucket exists and is writable before enabling access logs.
resource "aws_s3_bucket_policy" "alb_access_logs" {
  bucket = aws_s3_bucket.alb_access_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowELBPutAccessLogs"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${local.elb_account_ids[local.region]}:root"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_access_logs.arn}/alb/AWSLogs/${local.account_id}/*"
      },
      {
        Sid    = "AllowELBGetBucketAcl"
        Effect = "Allow"
        Principal = {
          Service = "elasticloadbalancing.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.alb_access_logs.arn
      }
    ]
  })

  # Ensure public access block is applied before the policy so we never have
  # a window where the policy exists without the hardening controls.
  depends_on = [aws_s3_bucket_public_access_block.alb_access_logs]
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = var.environment == "production"

  # Ethereum L1 TXs can take 600-900s to confirm.
  # Must exceed Facilitator TxWatcher (900s) + margin.
  idle_timeout = 960

  access_logs {
    bucket  = aws_s3_bucket.alb_access_logs.id
    enabled = true
    prefix  = "alb"
  }

  tags = {
    Name = "${local.name_prefix}-alb"
  }

  # ALB refuses to come up unless the bucket + policy are in place.
  depends_on = [aws_s3_bucket_policy.alb_access_logs]
}

# SSL Certificate - uses the certificate created in route53.tf
# Reference: aws_acm_certificate.main

# Target Groups
resource "aws_lb_target_group" "mcp_server" {
  name        = "${local.name_prefix}-mcp-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  # Must be <= stopTimeout (120s) in the container definition.
  # ALB stops sending NEW requests immediately, but keeps existing connections
  # open for this duration.  Phase B tasks are not HTTP connections (they're
  # internal asyncio tasks), but the container must stay alive for them.
  # 30s is enough for HTTP drain; the stopTimeout (120s) is what actually
  # keeps the container alive for Phase B.
  deregistration_delay = 30

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200-299"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 10
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${local.name_prefix}-mcp-tg"
  }
}

# Dashboard TG removed — dashboard is served via S3+CloudFront (dashboard-cdn.tf).

# HTTP Listener (redirect to HTTPS)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS Listener — default action returns 404 for unknown hosts.
# mcp.execution.market is routed via the listener rule below.
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main.certificate_arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not Found"
      status_code  = "404"
    }
  }
}

# Route mcp.execution.market → MCP server
resource "aws_lb_listener_rule" "mcp" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mcp_server.arn
  }

  condition {
    host_header {
      values = ["mcp.${var.domain_name}"]
    }
  }
}

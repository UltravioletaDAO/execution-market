# Execution Market Infrastructure — VPC Flow Logs
#
# PURPOSE
#   Capture IP traffic metadata for the em-production VPC. Flow logs are
#   essential for:
#     - Post-incident forensics (who hit the NAT gateway during an outage?)
#     - Security investigations (was traffic leaving to an unexpected IP?)
#     - Compliance (many frameworks require network-level audit trail).
#
# STATE BEFORE THIS FILE (verified 2026-04-21)
#   `aws ec2 describe-flow-logs --region us-east-2` returned an empty list.
#   Four VPCs exist in us-east-2; only the em-production VPC is in scope
#   for this project (facilitator-production, lighthouse-vpc-prod, and the
#   default VPC are owned by other projects/teams).
#
# DESTINATION: S3 vs CloudWatch Logs
#   Picked S3 for cost. Rationale:
#     - CloudWatch Logs ingest: $0.50/GB, storage $0.03/GB-mo.
#     - S3 storage: $0.023/GB-mo, zero ingest charge. Flow logs compress
#       well (gzip) so storage footprint is small.
#     - For our traffic volume (single ECS service, modest egress), CWL
#       would run ~$3-5/mo in ingest; S3 runs <$1/mo.
#     - Querying: Athena over S3 is the standard incident-response path.
#     - We keep flow logs 90 days (see lifecycle rule) — enough for
#       forensics windows without unbounded cost growth.
#
# TRAFFIC TYPE
#   ALL (accepted + rejected). Rejected traffic is the most interesting
#   signal for security investigations (port scans, failed exfil attempts).

# ── S3 Bucket for Flow Logs ──────────────────────────────────────────────────

resource "aws_s3_bucket" "vpc_flow_logs" {
  bucket        = "${local.name_prefix}-vpc-flow-logs-${local.account_id}"
  force_destroy = false

  tags = {
    Name    = "${local.name_prefix}-vpc-flow-logs"
    Purpose = "vpc-flow-logs-storage"
  }
}

resource "aws_s3_bucket_public_access_block" "vpc_flow_logs" {
  bucket = aws_s3_bucket.vpc_flow_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "vpc_flow_logs" {
  bucket = aws_s3_bucket.vpc_flow_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "vpc_flow_logs" {
  bucket = aws_s3_bucket.vpc_flow_logs.id
  versioning_configuration {
    status = "Disabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "vpc_flow_logs" {
  bucket = aws_s3_bucket.vpc_flow_logs.id

  rule {
    id     = "expire-after-90-days"
    status = "Enabled"

    filter {}

    expiration {
      days = 90
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

# Bucket policy allowing the VPC Flow Logs service to write objects.
# https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-s3.html#flow-logs-s3-permissions
data "aws_iam_policy_document" "vpc_flow_logs_bucket" {
  statement {
    sid    = "AWSLogDeliveryWrite"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["delivery.logs.amazonaws.com"]
    }
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.vpc_flow_logs.arn}/AWSLogs/${local.account_id}/*"]
    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:logs:${local.region}:${local.account_id}:*"]
    }
  }

  statement {
    sid    = "AWSLogDeliveryAclCheck"
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["delivery.logs.amazonaws.com"]
    }
    actions   = ["s3:GetBucketAcl", "s3:ListBucket"]
    resources = [aws_s3_bucket.vpc_flow_logs.arn]
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:logs:${local.region}:${local.account_id}:*"]
    }
  }
}

resource "aws_s3_bucket_policy" "vpc_flow_logs" {
  bucket = aws_s3_bucket.vpc_flow_logs.id
  policy = data.aws_iam_policy_document.vpc_flow_logs_bucket.json
}

# ── VPC Flow Log ─────────────────────────────────────────────────────────────

resource "aws_flow_log" "main_vpc" {
  vpc_id                   = aws_vpc.main.id
  traffic_type             = "ALL"
  log_destination_type     = "s3"
  log_destination          = aws_s3_bucket.vpc_flow_logs.arn
  max_aggregation_interval = 600

  # Hive-compatible partitioning keeps Athena scans cheap.
  destination_options {
    file_format                = "parquet"
    hive_compatible_partitions = true
    per_hour_partition         = true
  }

  tags = {
    Name = "${local.name_prefix}-vpc-flow-log"
  }

  depends_on = [aws_s3_bucket_policy.vpc_flow_logs]
}

# ── Outputs ──────────────────────────────────────────────────────────────────

output "vpc_flow_logs_s3_bucket" {
  description = "S3 bucket name where VPC flow logs are delivered."
  value       = aws_s3_bucket.vpc_flow_logs.id
}

output "vpc_flow_log_id" {
  description = "ID of the em-production VPC Flow Log."
  value       = aws_flow_log.main_vpc.id
}

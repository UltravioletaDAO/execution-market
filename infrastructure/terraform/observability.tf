# Execution Market Infrastructure - Security Observability
#
# GR-1.10: CloudTrail, GuardDuty, and IAM credential-creation alarms.
# Detects credential leaks, unauthorized access, and suspicious API calls.

# ── CloudTrail — multi-region, management events ────────────────────────────

resource "aws_cloudtrail" "main" {
  name                          = "${local.name_prefix}-cloudtrail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail_logs.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_logging                = true
  enable_log_file_validation    = true
  cloud_watch_logs_group_arn    = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
  cloud_watch_logs_role_arn     = aws_iam_role.cloudtrail_cloudwatch.arn

  # Capture management + data events across all regions
  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }

  tags = {
    Name = "${local.name_prefix}-cloudtrail"
  }

  depends_on = [aws_s3_bucket_policy.cloudtrail_logs]

  # Task 1.2: guard against a tainted-resource replace silently destroying the
  # trail. INC false-positive 2026-04-18 was a 535ms destroy/recreate; with
  # prevent_destroy a `terraform apply` that would delete this trail now errors
  # out instead of recreating it (and tripping the deletion alarm).
  lifecycle {
    prevent_destroy = true
  }
}

# ── CloudTrail S3 Bucket ────────────────────────────────────────────────────

resource "aws_s3_bucket" "cloudtrail_logs" {
  bucket = "${local.name_prefix}-cloudtrail-logs-${local.account_id}"

  tags = {
    Name = "${local.name_prefix}-cloudtrail-logs"
  }
}

resource "aws_s3_bucket_versioning" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    # Apply to all objects in bucket (required by aws provider >= 4.9)
    filter {}

    expiration {
      days = 365
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_policy" "cloudtrail_logs" {
  bucket = aws_s3_bucket.cloudtrail_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AWSCloudTrailAclCheck"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:GetBucketAcl"
        Resource  = aws_s3_bucket.cloudtrail_logs.arn
      },
      {
        Sid       = "AWSCloudTrailWrite"
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.cloudtrail_logs.arn}/AWSLogs/${local.account_id}/*"
        Condition = {
          StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" }
        }
      }
    ]
  })
}

# ── CloudWatch Log Group for CloudTrail ─────────────────────────────────────

resource "aws_cloudwatch_log_group" "cloudtrail" {
  name              = "/aws/cloudtrail/${local.name_prefix}"
  retention_in_days = 90

  tags = {
    Name = "${local.name_prefix}-cloudtrail-logs"
  }
}

# ── IAM Role for CloudTrail → CloudWatch ────────────────────────────────────

resource "aws_iam_role" "cloudtrail_cloudwatch" {
  name = "${local.name_prefix}-cloudtrail-cw-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "cloudtrail.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${local.name_prefix}-cloudtrail-cw-role"
  }
}

resource "aws_iam_role_policy" "cloudtrail_cloudwatch" {
  name = "${local.name_prefix}-cloudtrail-cw-policy"
  role = aws_iam_role.cloudtrail_cloudwatch.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
      }
    ]
  })
}

# ── CloudWatch Metric Filter + Alarm: CloudTrail Tampering (Task 1.2) ───────
# Detects: StopLogging, DeleteTrail, UpdateTrail, PutEventSelectors — the API
# calls that disable/alter audit logging. Excludes the Terraform deploy
# principals so a legitimate tainted-resource replace (e.g. INC 2026-04-18)
# does NOT page. Anyone else touching the trail = CRITICAL.

variable "cloudtrail_deploy_principal_arns" {
  description = "IAM principal ARNs allowed to mutate the CloudTrail trail (Terraform deploy identities). Excluded from the tampering alarm so legit `terraform apply` replaces don't page."
  type        = list(string)
  default = [
    "arn:aws:iam::518898403364:user/execution-market-deployer",
    "arn:aws:iam::518898403364:user/terraform-deployer",
  ]
}

resource "aws_cloudwatch_log_metric_filter" "cloudtrail_tampering" {
  name = "${local.name_prefix}-cloudtrail-tampering"
  # eventName in (StopLogging, DeleteTrail, UpdateTrail, PutEventSelectors)
  # AND actor ARN is not one of the deploy principals.
  pattern = join(" ", concat(
    ["{ (($.eventName = StopLogging) || ($.eventName = DeleteTrail) || ($.eventName = UpdateTrail) || ($.eventName = PutEventSelectors))"],
    [for arn in var.cloudtrail_deploy_principal_arns : "&& ($.userIdentity.arn != \"${arn}\")"],
    ["}"]
  ))
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name

  metric_transformation {
    name      = "CloudTrailTampering"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "cloudtrail_tampering" {
  alarm_name          = "${local.name_prefix}-cloudtrail-tampering"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CloudTrailTampering"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  # Treat "no data" as not-breaching so the alarm doesn't flap into INSUFFICIENT.
  treat_missing_data = "notBreaching"
  alarm_description  = "CRITICAL: CloudTrail trail was stopped/deleted/altered by a non-deploy principal (StopLogging/DeleteTrail/UpdateTrail/PutEventSelectors). Possible audit-log tampering."
  alarm_actions      = [aws_sns_topic.mcp_alerts.arn]
  ok_actions         = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-cloudtrail-tampering"
    Severity = "critical"
  }
}

# ── GuardDuty ───────────────────────────────────────────────────────────────

resource "aws_guardduty_detector" "main" {
  enable = true

  tags = {
    Name = "${local.name_prefix}-guardduty"
  }
}

# ── CloudWatch Metric Filter + Alarm: IAM Credential Creation ───────────────
# Detects: CreateUser, CreateAccessKey, PutBucketPolicy
# Critical for catching unauthorized credential creation after a key leak.

resource "aws_cloudwatch_log_metric_filter" "iam_credential_creation" {
  name           = "${local.name_prefix}-iam-credential-creation"
  pattern        = "{ ($.eventName = CreateUser) || ($.eventName = CreateAccessKey) || ($.eventName = PutBucketPolicy) }"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name

  metric_transformation {
    name      = "IAMCredentialCreation"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "iam_credential_creation" {
  alarm_name          = "${local.name_prefix}-iam-credential-creation"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "IAMCredentialCreation"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert on any IAM user/access key creation or bucket policy change"
  alarm_actions       = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-iam-credential-creation"
    Severity = "critical"
  }
}

# ── CloudWatch Metric Filter + Alarm: Console Sign-In Without MFA ───────────

resource "aws_cloudwatch_log_metric_filter" "console_signin_no_mfa" {
  name           = "${local.name_prefix}-console-signin-no-mfa"
  pattern        = "{ ($.eventName = ConsoleLogin) && ($.additionalEventData.MFAUsed != Yes) }"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name

  metric_transformation {
    name      = "ConsoleSignInNoMFA"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "console_signin_no_mfa" {
  alarm_name          = "${local.name_prefix}-console-signin-no-mfa"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ConsoleSignInNoMFA"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Alert on AWS console sign-in without MFA"
  alarm_actions       = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-console-signin-no-mfa"
    Severity = "critical"
  }
}

# ── CloudWatch Metric Filter + Alarm: Root Account Usage ────────────────────

resource "aws_cloudwatch_log_metric_filter" "root_account_usage" {
  name           = "${local.name_prefix}-root-account-usage"
  pattern        = "{ $.userIdentity.type = Root && $.userIdentity.invokedBy NOT EXISTS && $.eventType != AwsServiceEvent }"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name

  metric_transformation {
    name      = "RootAccountUsage"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "root_account_usage" {
  alarm_name          = "${local.name_prefix}-root-account-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RootAccountUsage"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  # Phase 3: this fires on ALL root activity (incl. read-only console logins,
  # e.g. legitimate admin sign-ins with hardware MFA), so it's noisy by design.
  # Demoted to INFO — the actionable signal is root_account_mutation below.
  # ok_actions sends a "root session ended" email when the 5-min window clears.
  alarm_description = "INFO: root account activity detected (any event, incl. read-only). Actionable mutations are alarmed separately by root-account-mutation."
  alarm_actions     = [aws_sns_topic.mcp_alerts.arn]
  ok_actions        = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-root-account-usage"
    Severity = "info"
  }
}

# ── CloudWatch Metric Filter + Alarm: Root Account Mutation (Phase 3) ────────
# The actionable root alarm: root activity where readOnly = false (writes /
# config changes), excluding AWS service events. Distinct from the broad
# root-account-usage alarm above, which stays INFO for read-only logins.

resource "aws_cloudwatch_log_metric_filter" "root_account_mutation" {
  name           = "${local.name_prefix}-root-account-mutation"
  pattern        = "{ $.userIdentity.type = Root && $.userIdentity.invokedBy NOT EXISTS && $.eventType != AwsServiceEvent && $.readOnly = false }"
  log_group_name = aws_cloudwatch_log_group.cloudtrail.name

  metric_transformation {
    name      = "RootAccountMutation"
    namespace = "CloudTrailMetrics"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "root_account_mutation" {
  alarm_name          = "${local.name_prefix}-root-account-mutation"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "RootAccountMutation"
  namespace           = "CloudTrailMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"
  alarm_description   = "CRITICAL: root account performed a mutating action (readOnly=false). Root should never write — investigate immediately."
  alarm_actions       = [aws_sns_topic.mcp_alerts.arn]
  ok_actions          = [aws_sns_topic.mcp_alerts.arn]

  tags = {
    Name     = "${local.name_prefix}-root-account-mutation"
    Severity = "critical"
  }
}

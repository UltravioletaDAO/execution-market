# Execution Market Infrastructure - Admin Dashboard (S3 + CloudFront)
#
# Static React SPA served via CloudFront from S3.
# URL: admin.execution.market
# Cost: ~$0.50/month (S3 + CloudFront free tier)
#
# Resources created via AWS CLI (2026-02-07), documented here for Terraform import:
#   - S3 bucket: em-production-admin-dashboard
#   - CloudFront distribution: E2IUZLTDUFIAQP (d10ucc05zs1fwn.cloudfront.net)
#   - CloudFront OAC: E3HPQ9VBJWQVDR
#   - ACM cert (us-east-1): arn:aws:acm:us-east-1:YOUR_AWS_ACCOUNT_ID:certificate/841084f8-b130-4b12-87ee-88ac7d81be24
#   - Route53 A record: admin.execution.market → CloudFront

locals {
  admin_bucket_name   = "em-production-admin-dashboard"
  admin_domain        = "admin.${var.domain}"
  admin_cloudfront_id = "E2IUZLTDUFIAQP"
  admin_oac_id        = "E3HPQ9VBJWQVDR"
  admin_acm_cert_arn  = "arn:aws:acm:us-east-1:YOUR_AWS_ACCOUNT_ID:certificate/841084f8-b130-4b12-87ee-88ac7d81be24"
}

# To import existing resources into Terraform state:
# terraform import aws_s3_bucket.admin_dashboard em-production-admin-dashboard
# terraform import aws_cloudfront_distribution.admin_dashboard E2IUZLTDUFIAQP
# terraform import aws_route53_record.admin_dashboard Z050891416D4N69E74FEN_admin.execution.market_A

# NOTE: Resources below are commented out to avoid conflicts with the
# CLI-created resources. Uncomment after running `terraform import`.

# resource "aws_s3_bucket" "admin_dashboard" {
#   bucket = local.admin_bucket_name
#   tags = {
#     Name    = "${local.name_prefix}-admin-dashboard"
#     Purpose = "admin-dashboard-hosting"
#   }
# }
#
# resource "aws_s3_bucket_public_access_block" "admin_dashboard" {
#   bucket                  = aws_s3_bucket.admin_dashboard.id
#   block_public_acls       = true
#   block_public_policy     = true
#   ignore_public_acls      = true
#   restrict_public_buckets = true
# }
#
# resource "aws_cloudfront_origin_access_control" "admin_dashboard" {
#   name                              = "em-admin-dashboard-oac"
#   description                       = "OAC for admin dashboard S3 bucket"
#   origin_access_control_origin_type = "s3"
#   signing_behavior                  = "always"
#   signing_protocol                  = "sigv4"
# }
#
# resource "aws_cloudfront_distribution" "admin_dashboard" {
#   origin {
#     domain_name              = "${local.admin_bucket_name}.s3.us-east-2.amazonaws.com"
#     origin_id                = "S3-em-admin-dashboard"
#     origin_access_control_id = aws_cloudfront_origin_access_control.admin_dashboard.id
#   }
#
#   enabled             = true
#   is_ipv6_enabled     = true
#   default_root_object = "index.html"
#   comment             = "Execution Market Admin Dashboard"
#   price_class         = "PriceClass_100"
#   http_version        = "http2and3"
#
#   aliases = [local.admin_domain]
#
#   default_cache_behavior {
#     allowed_methods  = ["GET", "HEAD"]
#     cached_methods   = ["GET", "HEAD"]
#     target_origin_id = "S3-em-admin-dashboard"
#     compress         = true
#
#     forwarded_values {
#       query_string = false
#       cookies { forward = "none" }
#     }
#
#     viewer_protocol_policy = "redirect-to-https"
#     min_ttl                = 0
#     default_ttl            = 86400
#     max_ttl                = 31536000
#   }
#
#   # SPA routing: return index.html for 403 (S3 returns 403 for missing keys)
#   custom_error_response {
#     error_code         = 403
#     response_code      = 200
#     response_page_path = "/index.html"
#     error_caching_min_ttl = 10
#   }
#
#   viewer_certificate {
#     acm_certificate_arn      = local.admin_acm_cert_arn
#     ssl_support_method       = "sni-only"
#     minimum_protocol_version = "TLSv1.2_2021"
#   }
#
#   restrictions {
#     geo_restriction { restriction_type = "none" }
#   }
#
#   tags = {
#     Name = "${local.name_prefix}-admin-dashboard-cdn"
#   }
# }
#
# resource "aws_s3_bucket_policy" "admin_dashboard" {
#   bucket = aws_s3_bucket.admin_dashboard.id
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Sid       = "AllowCloudFrontServicePrincipal"
#         Effect    = "Allow"
#         Principal = { Service = "cloudfront.amazonaws.com" }
#         Action    = "s3:GetObject"
#         Resource  = "${aws_s3_bucket.admin_dashboard.arn}/*"
#         Condition = {
#           StringEquals = {
#             "AWS:SourceArn" = aws_cloudfront_distribution.admin_dashboard.arn
#           }
#         }
#       }
#     ]
#   })
# }
#
# resource "aws_route53_record" "admin_dashboard" {
#   zone_id = data.aws_route53_zone.main.zone_id
#   name    = local.admin_domain
#   type    = "A"
#
#   alias {
#     name                   = aws_cloudfront_distribution.admin_dashboard.domain_name
#     zone_id                = aws_cloudfront_distribution.admin_dashboard.hosted_zone_id
#     evaluate_target_health = false
#   }
# }

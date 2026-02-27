---
date: 2026-02-26
tags:
  - domain/infrastructure
  - aws
  - s3
  - cdn
status: active
aliases:
  - CloudFront
  - S3
  - CDN
  - Evidence Storage
related-files:
  - infrastructure/
  - admin-dashboard/
---

# CloudFront & S3

Two distinct S3+CloudFront deployments serve different purposes in Execution Market.

## 1. Evidence Storage

**Purpose**: Workers upload photographic/documentary evidence for task submissions.

| Component | Details |
|-----------|---------|
| Upload | S3 presigned URLs (server generates, client uploads directly) |
| Delivery | CloudFront CDN (low-latency global access) |
| Access | Public read via CDN, write via presigned URL only |

Evidence URLs follow the pattern:
```
https://<distribution>.cloudfront.net/evidence/<task_id>/<filename>
```

## 2. Admin Dashboard

**Purpose**: Static hosting for the admin panel SPA.

| Component | Details |
|-----------|---------|
| Domain | `admin.execution.market` |
| Auth | `X-Admin-Key` header required |
| Hosting | S3 static website + CloudFront distribution |
| Source | `admin-dashboard/` directory |

## Security

- Evidence bucket: no public listing, only individual object access via CDN
- Admin bucket: CloudFront function validates `X-Admin-Key` before serving
- All transfers over HTTPS (CloudFront enforces TLS)

## Related

- [[alb-dns-routing]] -- DNS routing for admin.execution.market
- [[evidence-verification]] -- how evidence is validated after upload

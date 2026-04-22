---
date: 2026-04-21
tags:
  - type/architecture
  - domain/infrastructure
  - domain/operations
status: active
aliases:
  - AWS Topology
  - Cloud Architecture
related-files:
  - infrastructure/terraform/main.tf
  - infrastructure/terraform/vpc.tf
  - infrastructure/terraform/ecs.tf
  - infrastructure/terraform/alb.tf
  - infrastructure/terraform/dashboard-cdn.tf
  - infrastructure/terraform/verification_pipeline.tf
  - infrastructure/terraform/monitoring.tf
  - infrastructure/terraform/waf.tf
  - infrastructure/terraform/observability.tf
---

# AWS Infrastructure — Execution Market

Source of truth: `infrastructure/terraform/*.tf` (24 files, ~130 AWS resources). This document renders the Terraform graph as Mermaid so an operator can hold the whole topology in their head without reading HCL.

Region: **us-east-2** (workloads). CloudFront WAFs + ACM certs for CloudFront in **us-east-1** via the `aws.us_east_1` aliased provider declared in [`dashboard-cdn.tf`](../../infrastructure/terraform/dashboard-cdn.tf).

**Feature flags** (all default `false` — see [[#feature-flags-enable_-variables]]):
- `enable_scp_management`, `enable_mfa_enforcement`, `enable_vpc_flow_logs`, `enable_canary_health_checks`
- `enable_evidence_pipeline`, `enable_magika_alarm`, `otel_enabled`

Related: [[verification-pipeline-map]] · [[auth-discovery]] · [[payment-architecture]]

## 1. Edge → Compute (request flow)

Public clients (browsers, AI agents, x402 senders) reach three edges: CloudFront for static SPAs, ALB for the MCP API, and API Gateway for the optional evidence pipeline. A regional WAF fronts the ALB; a CloudFront-scoped WAF fronts the dashboard.

```mermaid
flowchart LR
    subgraph Clients
        Browser[Human browser]
        Agent[AI agent / MCP client]
        Upload[Evidence uploader]
    end

    subgraph DNS_TLS["Route53 + ACM"]
        R53[(Route53<br/>execution.market)]
        ACMus2[ACM us-east-2<br/>mcp + wildcard]
        ACMus1[ACM us-east-1<br/>dashboard / docs / admin]
    end

    subgraph Edge_CDN["CloudFront (global)"]
        CFDash[CF: execution.market<br/>+ www]
        CFDocs[CF: docs.execution.market]
        CFAdmin[CF: admin.execution.market]
        CFEvid[CF: storage.execution.market<br/>enable_evidence_pipeline]
        WAFCF[WAF CLOUDFRONT scope<br/>us-east-1]
    end

    subgraph Edge_ALB["ALB (us-east-2)"]
        ALB[Application LB<br/>idle_timeout 960s]
        WAFR[WAF REGIONAL<br/>6 rules]
    end

    subgraph Edge_APIGW["API Gateway v2 (evidence)"]
        APIGW[HTTP API<br/>enable_evidence_pipeline]
    end

    Browser --> R53
    Agent --> R53
    Upload --> R53

    R53 --> CFDash
    R53 --> CFDocs
    R53 --> CFAdmin
    R53 --> CFEvid
    R53 --> ALB
    R53 --> APIGW

    ACMus1 -.serves.-> CFDash
    ACMus1 -.serves.-> CFDocs
    ACMus1 -.serves.-> CFAdmin
    ACMus1 -.serves.-> CFEvid
    ACMus2 -.serves.-> ALB

    WAFCF -.attached.-> CFDash
    WAFR -.attached.-> ALB

    CFDash --> S3Dash[(S3<br/>dashboard SPA)]
    CFDocs --> S3Docs[(S3<br/>VitePress docs)]
    CFAdmin --> S3Admin[(S3<br/>admin SPA)]
    CFEvid --> S3Evid[(S3<br/>evidence)]

    ALB --> MCPTG[TG: mcp-server<br/>port 8000 / health]
    APIGW --> LPresign[λ evidence_presign]
    APIGW --> LAuthz[λ evidence_authorizer<br/>JWT HS256]

    MCPTG --> MCPSvc[ECS Fargate<br/>mcp-server svc]
```

## 2. VPC network topology

Single VPC, two public AZs (ALB), two private AZs (ECS tasks, Lambda, EFS). One NAT gateway for egress (cost-optimised). Two VPC gateway endpoints (S3, DynamoDB) bypass the NAT for the two highest-volume AWS services.

```mermaid
flowchart TB
    Internet((Internet))
    IGW[Internet Gateway]
    NAT[NAT Gateway<br/>+ EIP]

    subgraph VPC["VPC 10.0.0.0/16 · us-east-2"]
        subgraph PubA["Public subnet · AZ-a"]
            ALB_a[ALB ENI]
        end
        subgraph PubB["Public subnet · AZ-b"]
            ALB_b[ALB ENI]
            NAT
        end
        subgraph PrvA["Private subnet · AZ-a"]
            MCP_a[ECS mcp-server<br/>task ENI]
            XMTP_a[ECS xmtp-bot<br/>task ENI]
            EFS_a[EFS mount target]
            L_a[λ Ring1 / Ring2<br/>ENI]
        end
        subgraph PrvB["Private subnet · AZ-b"]
            MCP_b[ECS mcp-server<br/>task ENI]
            EFS_b[EFS mount target]
            L_b[λ Ring1 / Ring2<br/>ENI]
        end
        VPES3[[VPC endpoint<br/>S3 Gateway]]
        VPEDDB[[VPC endpoint<br/>DynamoDB Gateway]]

        SG_ALB{{SG alb<br/>in: 80,443/0.0.0.0/0}}
        SG_ECS{{SG ecs<br/>in: 8000 from SG_ALB}}
        SG_XMTP{{SG xmtp_bot<br/>egress only}}
        SG_EFS{{SG efs_xmtp<br/>in: 2049 from SG_XMTP}}
    end

    Internet --> IGW
    IGW --> PubA
    IGW --> PubB
    PrvA --> NAT
    PrvB --> NAT
    NAT --> IGW

    PrvA -.routes via.-> VPES3
    PrvA -.routes via.-> VPEDDB
    PrvB -.routes via.-> VPES3
    PrvB -.routes via.-> VPEDDB

    ALB_a -.-> SG_ALB
    ALB_b -.-> SG_ALB
    MCP_a -.-> SG_ECS
    MCP_b -.-> SG_ECS
    XMTP_a -.-> SG_XMTP
    EFS_a -.-> SG_EFS
    EFS_b -.-> SG_EFS
```

## 3. Compute + data services (MCP server + verification)

The MCP server task is the workload core. Its task role grants least-privilege writes to S3 evidence, DynamoDB (ERC-8128 nonce store), SQS (Ring 1/2 verification queues), and CloudWatch custom metrics. The execution role pulls ECR images and reads Secrets Manager.

Verification is fully asynchronous: MCP enqueues to SQS Ring 1 (PHOTINT), which fans out to Ring 2 (arbiter) on low-confidence results. Both queues have DLQs with composite alarms (backlog **and** age).

```mermaid
flowchart LR
    subgraph ECR["ECR (us-east-2)"]
        EMcp[(mcp-server)]
        EDash[(dashboard<br/>artifact only)]
        EXmtp[(xmtp-bot)]
        ERing1[(ring1-worker)]
        ERing2[(ring2-worker)]
    end

    subgraph ECS_Cluster["ECS Fargate cluster: em-production"]
        MCPT[Task def<br/>mcp-server<br/>1 vCPU / 2 GB]
        MCPSvc[Service mcp-server<br/>autoscale 1–4]
        OTEL[ADOT sidecar<br/>otel_enabled]
        XBot[Service xmtp-bot<br/>singleton]
    end

    subgraph IAM_Roles["IAM roles"]
        RExec[ecs_execution<br/>ECR pull + SM read + CWL]
        RTask[ecs_task<br/>S3 / SQS / DDB / CW / X-Ray]
        RXmtp[xmtp_bot_task<br/>EFS + SSM exec]
        RVer[verification_lambda<br/>SQS / SM / S3 / CWL]
    end

    subgraph Data
        DDB[(DynamoDB<br/>nonce_store<br/>TTL)]
        S3E[(S3 evidence<br/>versioned)]
        SMSentry[[SM: sentry_dsn]]
        SMEvid[[SM: evidence_jwt_secret]]
        SMXmtp[[SM: xmtp]]
        SMMesh[[SM: meshrelay]]
        EFS[(EFS xmtp_bot<br/>encrypted + IA 30d)]
    end

    subgraph Queues["SQS"]
        Q1[ring1<br/>vis 360s / ret 4d]
        Q1DLQ[ring1-dlq<br/>14d]
        Q2[ring2<br/>vis 240s / ret 4d]
        Q2DLQ[ring2-dlq<br/>14d]
    end

    subgraph Lambdas["Lambda"]
        L1[ring1-worker<br/>2048 MB / 300s / reserved 5]
        L2[ring2-worker<br/>512 MB / 180s / reserved 5]
    end

    EMcp -->|image| MCPT
    EXmtp -->|image| XBot
    ERing1 -->|image| L1
    ERing2 -->|image| L2

    MCPT --> MCPSvc
    MCPSvc -.logs.-> CWLMcp[/CWL mcp-server 90d/]
    OTEL -.logs.-> CWLOtel[/CWL otel-collector 30d/]
    MCPSvc -. uses .-> RExec
    MCPSvc -. uses .-> RTask
    XBot -. uses .-> RXmtp

    RExec -->|pull| EMcp
    RExec -->|pull| EXmtp
    RExec -->|read| SMSentry
    RTask -->|r/w| S3E
    RTask -->|r/w| DDB
    RTask -->|send| Q1
    RTask -->|send| Q2
    RXmtp -->|mount| EFS
    RXmtp -->|read| SMXmtp
    RXmtp -->|read| SMMesh

    Q1 -. redrive .-> Q1DLQ
    Q2 -. redrive .-> Q2DLQ
    Q1 -->|event source| L1
    Q2 -->|event source| L2
    L1 -->|fan-out| Q2
    L1 -. uses .-> RVer
    L2 -. uses .-> RVer
    RVer -->|read| S3E
```

## 4. Observability, audit, and alarms

CloudTrail (multi-region, log-file validation) lands in both S3 and CloudWatch Logs. Metric filters on the CWL trail drive three critical IAM alarms (credential creation, console sign-in without MFA, root account usage). Service alarms cover ECS task count, memory, ALB 5xx/4xx, unhealthy hosts, and WAF blocks.

```mermaid
flowchart TB
    subgraph Audit
        CT[CloudTrail main<br/>multi-region + LFV]
        CTS3[(S3 cloudtrail_logs<br/>90d Glacier → 365d expire)]
        CTCWL[/CWL cloudtrail 90d/]
    end

    subgraph Threat["Threat detection"]
        GD[GuardDuty detector]
        VFL[/VPC Flow Logs<br/>enable_vpc_flow_logs/]
        VFLS3[(S3 vpc-flow-logs<br/>Parquet + Hive · 90d)]
        WAFLog[/CWL waf · BLOCK only 90d/]
        WAFCFLog[/CWL waf-cloudfront<br/>us-east-1 · 30d/]
    end

    subgraph Filters["CWL metric filters"]
        FCred[IAMCredentialCreation]
        FMFA[ConsoleSignInNoMFA]
        FRoot[RootAccountUsage]
    end

    subgraph Alarms_Crit["CRITICAL alarms"]
        AMcpDown[mcp no_running_tasks]
        A5xx[mcp 5xx > 5/min]
        ACred[iam credential creation]
        ANoMFA[console signin no mfa]
        ARoot[root account usage]
    end

    subgraph Alarms_Warn["WARNING alarms"]
        AMem[mcp memory > 80%]
        A4xx[mcp 4xx spike > 50/min]
        AUnh[mcp unhealthy hosts]
        AWaf[waf blocked > 100/5min]
        AMag[magika rejection > 5%<br/>enable_magika_alarm]
        A1stuck[ring1 DLQ stuck<br/>composite]
        A2stuck[ring2 DLQ stuck<br/>composite]
        AXmtpDown[xmtp not running]
        AXmtpMem[xmtp memory > 85%]
    end

    subgraph Canary["Canary · enable_canary_health_checks"]
        HCmcp[Route53 HC<br/>mcp.execution.market]
        HCdash[Route53 HC<br/>execution.market]
        HCadm[Route53 HC<br/>admin.execution.market]
        ACAN1[canary mcp down<br/>us-east-1]
        ACAN2[canary dashboard<br/>us-east-1]
        ACAN3[canary admin<br/>us-east-1]
    end

    SNS[[SNS mcp_alerts]]
    SNSX[[SNS xmtp_bot_alerts]]
    Email[[Email subscription<br/>alert_email]]

    CT --> CTS3
    CT --> CTCWL
    CTCWL --> FCred --> ACred
    CTCWL --> FMFA --> ANoMFA
    CTCWL --> FRoot --> ARoot

    VFL --> VFLS3

    Alarms_Crit --> SNS
    Alarms_Warn --> SNS
    Canary --> SNS
    AXmtpDown --> SNSX
    AXmtpMem --> SNSX
    SNS --> Email
    SNSX --> Email

    HCmcp --> ACAN1
    HCdash --> ACAN2
    HCadm --> ACAN3
```

## 5. IAM, organizations, and guardrails

Four enforcement layers protect the account. Two are always on (WAF logging filter, CI `internal-notes-check` + `terraform-validate`, local pre-commit hook). Two are declared in code but gated behind `enable_*` variables because the CI deploy user (`execution-market-deployer`) lacks the permissions and they are admin-applied.

```mermaid
flowchart LR
    subgraph AlwaysOn["Always-on guardrails"]
        PC[Pre-commit hook<br/>scans staged diff]
        CIIN[CI internal-notes-check]
        CITF[CI terraform-validate]
        WL[WAF logging_filter<br/>BLOCK-only]
    end

    subgraph AdminGated["Gated (admin apply)"]
        SCP[SCP deny root principal<br/>enable_scp_management]
        MFA[IAM ForceMFA policy<br/>enable_mfa_enforcement]
        VFL2[VPC Flow Logs<br/>enable_vpc_flow_logs]
        CAN[Route53 canaries<br/>enable_canary_health_checks]
    end

    subgraph Roles["Runtime roles"]
        RExec2[ecs_execution]
        RTask2[ecs_task]
        RXmtp2[xmtp_bot_task]
        RVer2[verification_lambda]
        REvid[evidence_lambda<br/>+ authorizer]
        RCT[cloudtrail_cloudwatch]
    end

    subgraph HumanUsers["Human users"]
        lxhxr[lxhxr<br/>MFA ✓]
        kadrez[kadrez<br/>MFA ✗ → first target]
        cuchorapido[cuchorapido<br/>MFA ✗]
    end

    MFA -. attach to .-> kadrez
    MFA -. safe no-op .-> lxhxr
    MFA -. coordinate .-> cuchorapido

    SCP -. applies to .-> Members[Member accounts<br/>NOT mgmt account]
```

## 6. Feature flags (`enable_*` variables)

All defined in [`variables.tf`](../../infrastructure/terraform/variables.tf). Keep defaults `false` so CI continues to work; flip to `true` from an admin workstation with full IAM / Organizations / EC2 permissions.

| Variable | Default | Gates | Reason default is `false` |
|---|---|---|---|
| `enable_scp_management` | `false` | [`organizations_scp.tf`](../../infrastructure/terraform/organizations_scp.tf) | CI user lacks `organizations:DescribeOrganization` (run 24749184610) |
| `enable_mfa_enforcement` | `false` | [`iam_mfa_enforcement.tf`](../../infrastructure/terraform/iam_mfa_enforcement.tf) | CI user lacks `iam:CreatePolicy` (run 24749420481) |
| `enable_vpc_flow_logs` | `false` | [`vpc_flow_logs.tf`](../../infrastructure/terraform/vpc_flow_logs.tf) | CI user lacks `ec2:CreateFlowLogs` (run 24749420481) |
| `enable_canary_health_checks` | `false` | [`canary_health.tf`](../../infrastructure/terraform/canary_health.tf) | Route53 alarms must be in us-east-1; ~$3/mo cost (run 24749420481) |
| `enable_evidence_pipeline` | `false` | [`evidence.tf`](../../infrastructure/terraform/evidence.tf) | Optional managed upload stack |
| `enable_magika_alarm` | `false` | [`monitoring.tf`](../../infrastructure/terraform/monitoring.tf) | Requires custom metric emission live in ECS first |
| `otel_enabled` | `false` | [`ecs.tf`](../../infrastructure/terraform/ecs.tf) | Turns on ADOT sidecar + X-Ray exporter |

## 7. Domain / sub-domain map

```mermaid
flowchart LR
    execution-market[[execution.market]] -->|A alias| CFDash2[CF dashboard]
    www[[www.execution.market]] -->|A alias| CFDash2
    docs[[docs.execution.market]] -->|A alias| CFDocs2[CF docs]
    admin[[admin.execution.market]] -->|A alias| CFAdmin2[CF admin]
    storage[[storage.execution.market]] -->|A alias| CFEvid2[CF evidence]
    mcp[[mcp.execution.market]] -->|A alias| ALB2[ALB]
    api[[api.execution.market]] -.planned.-> ALB2
```

## 8. Cross-references

- [[verification-pipeline-map]] — Ring 1 / Ring 2 internals
- [[auth-discovery]] — auth endpoints served by MCP
- [[magika-ring1-ring2-flow]] — verification decision flow
- [[payment-architecture]] — agent-signed escrow (ADR-001)
- [[adr/ADR-001-payment-architecture-v2]] — payment ADR

## 9. Change log

| Date | Change |
|---|---|
| 2026-04-21 | Initial document. Reflects commit `c7923e92` — 4 new `enable_*` flags added after deploy runs 24749184610 + 24749420481 exposed CI user permission gaps. |

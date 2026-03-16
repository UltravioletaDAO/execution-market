---
name: deploy-xmtp-bot
description: Deploy XMTP Bot to ECS Fargate
---

# Deploy XMTP Bot

Manual deployment of the XMTP bot service to ECS Fargate.

## Steps

1. **ECR Login**
```bash
MSYS_NO_PATHCONV=1 aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com
```

2. **Build Docker Image**
```bash
cd xmtp-bot && docker build --no-cache --platform linux/amd64 -t em-xmtp-bot:latest .
```

3. **Tag and Push to ECR**
```bash
docker tag em-xmtp-bot:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/em-production-xmtp-bot:latest
docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-2.amazonaws.com/em-production-xmtp-bot:latest
```

4. **Force New Deployment**
```bash
MSYS_NO_PATHCONV=1 aws ecs update-service --cluster em-production --service em-xmtp-bot --force-new-deployment --region us-east-2
```

5. **Verify Health** (wait ~90s)
```bash
sleep 90
MSYS_NO_PATHCONV=1 aws ecs describe-services --cluster em-production --services em-xmtp-bot --region us-east-2 --query 'services[0].{status:status,running:runningCount,desired:desiredCount,deployments:deployments[*].{status:status,running:runningCount}}'
```

## Troubleshooting

- **Task keeps restarting**: Check CloudWatch logs at `/ecs/em-xmtp-bot`
- **EFS mount fails**: Verify security group allows NFS (2049) from bot SG to EFS SG
- **XMTP connection fails**: Verify `XMTP_WALLET_KEY` in Secrets Manager `em/xmtp`
- **DB lost**: Restore from EFS backup. WARNING: new installation burns 1 of 10 slots (30min cooldown)

## Important

- ALWAYS use `MSYS_NO_PATHCONV=1` prefix on Windows Git Bash
- Bot is singleton (desired_count=1) — do NOT scale horizontally
- EFS mount persists XMTP SQLite DB — losing it requires new wallet registration

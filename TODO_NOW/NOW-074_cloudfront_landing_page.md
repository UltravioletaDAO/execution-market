# NOW-074: CloudFront Landing Page Setup

## Status: REQUIRED (for static landing page)
## Priority: P1

## Overview

Para tener el sitio online rápidamente sin ECS, se usa S3 + CloudFront para la landing page estática.

## Paso 1: Crear S3 Bucket

```bash
# Crear bucket para landing page
aws s3 mb s3://chamba-landing-ultravioleta --region us-east-2

# Configurar como website
aws s3 website s3://chamba-landing-ultravioleta \
  --index-document index.html \
  --error-document index.html

# Bucket policy para acceso público (crear archivo policy.json)
cat > /tmp/bucket-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::chamba-landing-ultravioleta/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket chamba-landing-ultravioleta \
  --policy file:///tmp/bucket-policy.json
```

## Paso 2: Subir Landing Page

```bash
# Desde ideas/chamba/landing/
aws s3 sync . s3://chamba-landing-ultravioleta/ --delete
```

## Paso 3: Crear ACM Certificate (DEBE ser us-east-1 para CloudFront)

```bash
# Solicitar certificado
aws acm request-certificate \
  --domain-name chamba.ultravioletadao.xyz \
  --validation-method DNS \
  --region us-east-1

# Obtener datos de validación DNS
aws acm describe-certificate \
  --certificate-arn <ARN_DEL_CERTIFICADO> \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions'
```

## Paso 4: Validar Certificado via DNS

Crear CNAME record en Route53 con los valores de validación.

## Paso 5: Crear CloudFront Distribution

```bash
# Usar archivo de configuración (ver cf-update.json en root)
aws cloudfront create-distribution \
  --distribution-config file://cf-config.json
```

## Paso 6: Configurar DNS

```bash
# Obtener CloudFront domain
CLOUDFRONT_DOMAIN=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Aliases.Items[0]=='chamba.ultravioletadao.xyz'].DomainName" \
  --output text)

# Crear/actualizar A record como alias a CloudFront
aws route53 change-resource-record-sets \
  --hosted-zone-id Z05485241GVL9TJOHP0TM \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "chamba.ultravioletadao.xyz",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2FDTNDATAQYW2",
          "DNSName": "'$CLOUDFRONT_DOMAIN'",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'
```

## Verificar

```bash
# Debe retornar 200 OK
curl -I https://chamba.ultravioletadao.xyz

# Headers esperados
# X-Cache: Hit from cloudfront
# Server: AmazonS3
```

## Notas

- CloudFront HostedZoneId siempre es `Z2FDTNDATAQYW2` (constante de AWS)
- Propagación DNS puede tomar 5-15 minutos
- CloudFront cache puede tomar hasta 24h (usar invalidation si necesario)

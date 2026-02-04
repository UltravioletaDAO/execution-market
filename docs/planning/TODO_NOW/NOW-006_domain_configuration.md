# NOW-006: Configurar dominio execution.market

## Metadata
- **Prioridad**: P0
- **Fase**: 0 - Infrastructure
- **Dependencias**: NOW-004
- **Archivos a modificar**: `infrastructure/terraform/route53.tf`
- **Tiempo estimado**: 30-60 min

## Descripción
Configurar DNS para el dominio execution.market con subdomains para API y App.

## Contexto Técnico
- **Domain**: execution.market
- **Subdomains**:
  - `api.execution.market` → MCP Server (ALB)
  - `app.execution.market` → Dashboard (ALB)
- **SSL**: ACM Certificate (auto-renewal)
- **Provider**: Route53

## Estructura DNS

```
execution.market
├── api.execution.market  → ALB (MCP Server)
├── app.execution.market  → ALB (Dashboard)
└── (root)                       → Redirect to app.
```

## Código de Referencia

### route53.tf
```hcl
# Data source for existing hosted zone
data "aws_route53_zone" "ultravioleta" {
  name = "ultravioleta.xyz"
}

# ACM Certificate
resource "aws_acm_certificate" "chamba" {
  domain_name               = "execution.market"
  subject_alternative_names = [
    "*.execution.market"
  ]
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# Certificate validation records
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.chamba.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id = data.aws_route53_zone.ultravioleta.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

# Wait for certificate validation
resource "aws_acm_certificate_validation" "chamba" {
  certificate_arn         = aws_acm_certificate.chamba.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# API subdomain
resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.ultravioleta.zone_id
  name    = "api.execution.market"
  type    = "A"

  alias {
    name                   = aws_lb.chamba.dns_name
    zone_id                = aws_lb.chamba.zone_id
    evaluate_target_health = true
  }
}

# App subdomain
resource "aws_route53_record" "app" {
  zone_id = data.aws_route53_zone.ultravioleta.zone_id
  name    = "app.execution.market"
  type    = "A"

  alias {
    name                   = aws_lb.chamba.dns_name
    zone_id                = aws_lb.chamba.zone_id
    evaluate_target_health = true
  }
}

# Root domain redirect (optional)
resource "aws_route53_record" "root" {
  zone_id = data.aws_route53_zone.ultravioleta.zone_id
  name    = "execution.market"
  type    = "A"

  alias {
    name                   = aws_lb.chamba.dns_name
    zone_id                = aws_lb.chamba.zone_id
    evaluate_target_health = true
  }
}
```

### ALB HTTPS Listener (alb.tf)
```hcl
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.chamba.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.chamba.certificate_arn

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not Found"
      status_code  = "404"
    }
  }
}

# Route api.* to MCP Server
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mcp_server.arn
  }

  condition {
    host_header {
      values = ["api.execution.market"]
    }
  }
}

# Route app.* to Dashboard
resource "aws_lb_listener_rule" "app" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.dashboard.arn
  }

  condition {
    host_header {
      values = ["app.execution.market"]
    }
  }
}
```

## Criterios de Éxito
- [ ] Certificate emitido y validado
- [ ] DNS records creados
- [ ] `api.execution.market` resuelve al ALB
- [ ] `app.execution.market` resuelve al ALB
- [ ] HTTPS funciona sin warnings
- [ ] HTTP redirects a HTTPS

## Comandos de Verificación
```bash
# DNS resolution
dig api.execution.market
dig app.execution.market

# SSL check
curl -vI https://api.execution.market/health
curl -vI https://app.execution.market/

# Certificate info
echo | openssl s_client -servername api.execution.market -connect api.execution.market:443 2>/dev/null | openssl x509 -noout -dates
```

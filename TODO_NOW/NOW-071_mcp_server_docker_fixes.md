# NOW-071: MCP Server Docker Build Fixes

## Status: REQUIRED
## Priority: P0 - Blocker for deployment

## Problem 1: websockets version conflict

**Error**:
```
fastmcp 2.14.4 depends on websockets>=15.0.1
realtime 2.27.2 depends on websockets<16
```

**Fix** - Editar `mcp_server/requirements.txt`:

```diff
- websockets>=12.0
+ websockets>=15.0,<16
```

## Problem 2: web3 geth_poa_middleware deprecation

**Error**:
```
ImportError: cannot import name 'geth_poa_middleware' from 'web3.middleware'
```

**Fix** - Editar `mcp_server/integrations/x402/client.py`:

```python
# Cambiar esto:
from web3.middleware import geth_poa_middleware

# Por esto:
try:
    from web3.middleware import ExtraDataToPOAMiddleware as geth_poa_middleware
except ImportError:
    try:
        from web3.middleware import geth_poa_middleware
    except ImportError:
        geth_poa_middleware = None
```

Y donde se usa:
```python
# Cambiar:
self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Por:
if geth_poa_middleware:
    self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
```

## Build Command

```bash
# Desde mcp_server/
docker build --no-cache --platform linux/amd64 -t chamba-mcp-server:latest .
```

## Verificar Build Exitoso

Debe terminar con:
```
Successfully built <sha256>
Successfully tagged chamba-mcp-server:latest
```

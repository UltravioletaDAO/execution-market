"""
ERC-8128: Signed HTTP Requests with Ethereum

Authenticate HTTP requests using HTTP Message Signatures (RFC 9421) with
Ethereum accounts. The same wallet that pays is the wallet that authenticates.

Components:
- verifier: Parse & verify ERC-8128 signed HTTP requests
- nonce_store: Single-use nonce management (DynamoDB / in-memory)
- erc1271: Smart contract account signature verification (ERC-1271)

Usage::

    from integrations.erc8128 import verify_erc8128_request, get_nonce_store

    result = await verify_erc8128_request(request, nonce_store=get_nonce_store())
    if result.ok:
        print(f"Authenticated wallet: {result.address}")
"""

from .verifier import (
    verify_erc8128_request,
    ERC8128Result,
    VerifyPolicy,
    DEFAULT_POLICY,
)
from .nonce_store import (
    NonceStore,
    InMemoryNonceStore,
    DynamoDBNonceStore,
    get_nonce_store,
)

__all__ = [
    "verify_erc8128_request",
    "ERC8128Result",
    "VerifyPolicy",
    "DEFAULT_POLICY",
    "NonceStore",
    "InMemoryNonceStore",
    "DynamoDBNonceStore",
    "get_nonce_store",
]

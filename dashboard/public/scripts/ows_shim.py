"""
OWS Python shim -- wraps the OWS CLI binary as a Python module.
Enables uvd-x402-sdk OWSWalletAdapter to work with OWS CLI v1.2.0+.

Install:
    SITE=$(python3 -c "import site; print(site.getusersitepackages())")
    mkdir -p "$SITE/ows"
    curl -sf https://execution.market/scripts/ows_shim.py > "$SITE/ows/__init__.py"

Author: Clawd (from live testing Apr 3, 2026)
"""

import subprocess
import json
from typing import Optional


class OWSWallet:
    def __init__(self, name, passphrase=None):
        self.name = name
        self._address = None

    @property
    def address(self):
        if not self._address:
            r = subprocess.run(
                ["ows", "wallet", "list"], capture_output=True, text=True
            )
            current_name = None
            in_target = False
            for line in r.stdout.splitlines():
                stripped = line.strip()
                if stripped.startswith("Name:"):
                    current_name = stripped.split(":", 1)[1].strip()
                    in_target = (current_name == self.name)
                    continue
                if in_target and "eip155" in line.lower() and "0x" in line:
                    parts = line.split()
                    for p in parts:
                        if p.startswith("0x") and len(p) == 42:
                            self._address = p
                            return self._address
        return self._address


class OWSSignResult:
    def __init__(
        self,
        signature=None,
        v=None,
        r=None,
        s=None,
        raw_transaction=None,
        from_address=None,
    ):
        self.signature = signature
        self.v = v
        self.r = r
        self.s = s
        self.raw_transaction = raw_transaction
        self.from_address = from_address


def _fix_sig(sig_hex, recovery_id=27):
    """Fix OWS CLI v1.2.0 bug: 64-byte sig missing v byte."""
    s = sig_hex[2:] if sig_hex.startswith("0x") else sig_hex
    if len(s) == 128:
        v = recovery_id if recovery_id >= 27 else recovery_id + 27
        s = s + format(v, "02x")
    return "0x" + s


def get_wallet(wallet_name, passphrase=None):
    return OWSWallet(wallet_name, passphrase)


def sign_message(wallet_name, message, passphrase=None):
    r = subprocess.run(
        [
            "ows",
            "sign",
            "message",
            "--chain",
            "ethereum",
            "--wallet",
            wallet_name,
            "--message",
            message,
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise Exception(f"ows sign message failed: {r.stderr}")
    d = json.loads(r.stdout)
    fixed = _fix_sig(d.get("signature", ""), d.get("recoveryId", 27))
    return OWSSignResult(signature=fixed)


def sign_transaction(wallet_name, transaction, passphrase=None):
    rpc_url = transaction.pop("_rpc_url", None) or "https://mainnet.base.org"
    from eth_account._utils.typed_transactions import TypedTransaction

    unsigned = TypedTransaction.from_dict(transaction)
    tx_hex = unsigned.hash().hex()
    r = subprocess.run(
        [
            "ows",
            "sign",
            "send-tx",
            "--chain",
            "ethereum",
            "--wallet",
            wallet_name,
            "--tx",
            tx_hex,
            "--rpc-url",
            rpc_url,
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise Exception(f"ows sign send-tx failed: {r.stderr}")
    d = json.loads(r.stdout)
    return OWSSignResult(
        raw_transaction=d.get("rawTransaction") or d.get("signedTx"),
    )


def _convert_bytes(obj):
    """Recursively convert bytes to 0x-prefixed hex strings for JSON."""
    if isinstance(obj, bytes):
        return "0x" + obj.hex()
    elif isinstance(obj, dict):
        return {k: _convert_bytes(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_convert_bytes(v) for v in obj]
    return obj


def sign_typed_data(wallet_name, domain, types, message, passphrase=None):
    # Determine primaryType (the non-EIP712Domain type)
    primary_type = next(k for k in types if k != "EIP712Domain")
    # OWS CLI v1.2.4 REQUIRES EIP712Domain in types — add if missing
    all_types = dict(types)
    if "EIP712Domain" not in all_types:
        # Infer EIP712Domain fields from the domain dict
        domain_fields = []
        field_order = [("name", "string"), ("version", "string"), ("chainId", "uint256"), ("verifyingContract", "address"), ("salt", "bytes32")]
        conv_domain = _convert_bytes(domain)
        for fname, ftype in field_order:
            if fname in conv_domain:
                domain_fields.append({"name": fname, "type": ftype})
        all_types["EIP712Domain"] = domain_fields
    typed_data_json = json.dumps(
        _convert_bytes({
            "types": all_types,
            "primaryType": primary_type,
            "domain": domain,
            "message": message,
        }),
        separators=(",", ":"),
    )
    r = subprocess.run(
        [
            "ows",
            "sign",
            "message",
            "--chain",
            "ethereum",
            "--wallet",
            wallet_name,
            "--message",
            "eip712",
            "--typed-data",
            typed_data_json,
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        raise Exception(f"ows sign typed-data failed: {r.stderr}")
    d = json.loads(r.stdout)
    fixed = _fix_sig(d.get("signature", ""), d.get("recoveryId", 27))
    return OWSSignResult(signature=fixed)


def sign_eip3009(
    wallet_name,
    to,
    value,
    valid_after,
    valid_before,
    nonce,
    chain_id,
    token_address,
    domain_name,
    domain_version,
    passphrase=None,
):
    typed_data = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "ReceiveWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        "domain": {
            "name": domain_name,
            "version": domain_version,
            "chainId": chain_id,
            "verifyingContract": token_address,
        },
        "message": {
            "from": get_wallet(wallet_name).address,
            "to": to,
            "value": value,
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce,
        },
    }
    result = sign_typed_data(
        wallet_name,
        typed_data["domain"],
        typed_data["types"],
        typed_data["message"],
        passphrase,
    )
    sig = (
        result.signature[2:]
        if result.signature.startswith("0x")
        else result.signature
    )
    r_val = "0x" + sig[:64]
    s_val = "0x" + sig[64:128]
    v_val = int(sig[128:130], 16) if len(sig) >= 130 else 27
    return OWSSignResult(
        signature=result.signature,
        v=v_val,
        r=r_val,
        s=s_val,
        from_address=get_wallet(wallet_name).address,
    )

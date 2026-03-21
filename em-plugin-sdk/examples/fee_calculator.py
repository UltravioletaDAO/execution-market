"""Offline fee calculator — no network calls needed."""

from em_plugin_sdk import calculate_fee, calculate_reverse_fee, get_fee_rate
from em_plugin_sdk import is_valid_pair, get_supported_tokens, get_escrow_networks

# Calculate what a worker receives from a $10 bounty
fee = calculate_fee(10.00, "physical_presence")
print(f"Bounty:     ${fee.gross_amount:.2f}")
print(f"Fee ({fee.fee_rate_percent:.0f}%):  ${fee.fee_amount:.2f}")
print(f"Worker gets: ${fee.worker_amount:.2f}")
print()

# Reverse: what bounty to post so worker gets exactly $10
rev = calculate_reverse_fee(10.00, "simple_action")
print(f"To pay worker $10.00, post bounty of ${rev.gross_amount:.2f}")
print()

# Fee rates by category
for cat in ["human_authority", "knowledge_access", "physical_presence"]:
    print(f"  {cat}: {get_fee_rate(cat) * 100:.0f}%")
print()

# Network/token validation
print(f"base + USDC valid? {is_valid_pair('base', 'USDC')}")
print(f"base + PYUSD valid? {is_valid_pair('base', 'PYUSD')}")
print(f"Ethereum tokens: {get_supported_tokens('ethereum')}")
print(f"Escrow networks: {get_escrow_networks()}")

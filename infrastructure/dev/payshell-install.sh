#!/usr/bin/env bash
# Phase 1.3 — Install pay.sh CLI from upstream (solana-foundation/pay).
# Doc: docs/runbooks/surfpool-payshell-dev-env.md
#
# Requires: rust toolchain (rustup), git, ~$2GB free disk for cargo target/

set -euo pipefail

INSTALL_DIR="${PAYSHELL_INSTALL_DIR:-$HOME/.local/share/payshell}"
PIN_COMMIT="${PAYSHELL_COMMIT:-main}"  # Pin a SHA when one is known-good.
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

if ! command -v cargo >/dev/null 2>&1; then
  echo "[FATAL] cargo not found. Install Rust via https://rustup.rs/" >&2
  exit 1
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR"

if [[ ! -d "$INSTALL_DIR/.git" ]]; then
  echo "[INFO] cloning solana-foundation/pay"
  git clone https://github.com/solana-foundation/pay.git "$INSTALL_DIR"
else
  echo "[INFO] updating $INSTALL_DIR"
  git -C "$INSTALL_DIR" fetch origin
fi

git -C "$INSTALL_DIR" checkout "$PIN_COMMIT"

echo "[INFO] building pay (release)"
cargo build --release --manifest-path "$INSTALL_DIR/Cargo.toml"

ln -sf "$INSTALL_DIR/target/release/pay" "$BIN_DIR/pay"

if ! command -v pay >/dev/null 2>&1; then
  echo "[WARN] $BIN_DIR is not on PATH. Add: export PATH=\"$BIN_DIR:\$PATH\"" >&2
else
  echo "[OK] pay installed: $(pay --version 2>/dev/null || echo 'pay --version failed — check upstream CLI flags')"
fi

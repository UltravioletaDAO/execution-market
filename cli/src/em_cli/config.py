"""
Configuration management for Execution Market CLI.

Stores OWS wallet identity (name + EVM address) per profile. The private
key NEVER lives in this config — it stays encrypted in the OWS vault.
Auth to the API is wallet-based ERC-8128 signing (see api.py + the
canonical signer in `execution_market._signer`).

Migration v1.0.0 (2026-05-28): API key auth removed (backend disabled
it with `EM_API_KEYS_ENABLED=false`). Existing profiles with `api_key`
are migrated on load — the field is dropped silently. Users re-run
`em login` to bind a wallet.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


# Default configuration directory
DEFAULT_CONFIG_DIR = Path.home() / ".execution-market"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_API_URL = "https://api.execution.market"
DEFAULT_CHAIN_ID = 8453  # Base mainnet


@dataclass
class Profile:
    """An Execution Market CLI profile — wallet-based auth (ERC-8128 via OWS)."""

    name: str
    wallet_name: str            # OWS wallet identifier (`ows wallet list`)
    wallet_address: str         # 0x... EVM address (same on all EVM chains)
    chain_id: int = DEFAULT_CHAIN_ID
    api_url: str = DEFAULT_API_URL
    default_payment_token: str = "USDC"
    default_timeout: float = 30.0
    output_format: str = "table"  # table, json
    executor_id: Optional[str] = None  # For worker profiles
    agent_id: Optional[int] = None     # Cached ERC-8004 numeric agent ID on this chain

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        """Create profile from dictionary; silently drops legacy `api_key` field."""
        # Strip any field this dataclass no longer accepts (notably api_key from
        # pre-1.0.0 configs). Avoids TypeError on schema migration.
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


@dataclass
class Config:
    """Execution Market CLI configuration."""

    active_profile: str = "default"
    profiles: Dict[str, Profile] = field(default_factory=dict)

    def get_active_profile(self) -> Optional[Profile]:
        """Get the currently active profile."""
        return self.profiles.get(self.active_profile)

    def set_active_profile(self, name: str) -> bool:
        """Set the active profile."""
        if name not in self.profiles:
            return False
        self.active_profile = name
        return True

    def add_profile(self, profile: Profile) -> None:
        """Add or update a profile."""
        self.profiles[profile.name] = profile

    def remove_profile(self, name: str) -> bool:
        """Remove a profile."""
        if name not in self.profiles:
            return False
        if name == self.active_profile and len(self.profiles) > 1:
            # Switch to another profile
            other = next(n for n in self.profiles.keys() if n != name)
            self.active_profile = other
        del self.profiles[name]
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "active_profile": self.active_profile,
            "profiles": {
                name: profile.to_dict()
                for name, profile in self.profiles.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        profiles = {
            name: Profile.from_dict(profile_data)
            for name, profile_data in data.get("profiles", {}).items()
        }
        return cls(
            active_profile=data.get("active_profile", "default"),
            profiles=profiles,
        )


class ConfigManager:
    """Manages Execution Market CLI configuration."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize config manager.

        Args:
            config_dir: Custom config directory (default: ~/.execution-market)
        """
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / "config.json"
        self._config: Optional[Config] = None

    @property
    def config(self) -> Config:
        """Get current configuration, loading from file if needed."""
        if self._config is None:
            self._config = self.load()
        return self._config

    def ensure_config_dir(self) -> None:
        """Ensure configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        # Set restrictive permissions on config directory
        if os.name != "nt":  # Not Windows
            self.config_dir.chmod(0o700)

    def load(self) -> Config:
        """Load configuration from file."""
        if not self.config_file.exists():
            return Config()

        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
            return Config.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            # Return empty config if file is corrupted
            return Config()

    def save(self) -> None:
        """Save configuration to file."""
        self.ensure_config_dir()

        with open(self.config_file, "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)

        # Set restrictive permissions on config file
        if os.name != "nt":  # Not Windows
            self.config_file.chmod(0o600)

    # ------------------------------------------------------------------
    # Wallet identity (replaces the v0.x get_api_key / set api_key path)
    # ------------------------------------------------------------------

    def get_wallet(self, profile_name: Optional[str] = None) -> Optional[tuple[str, str, int]]:
        """
        Return (wallet_name, wallet_address, chain_id) for signing, with env overrides.

        Priority:
        1. EM_WALLET_NAME + EM_WALLET_ADDRESS env vars (with EM_CHAIN_ID optional)
        2. Profile in config

        Returns None if no wallet is configured anywhere.
        """
        env_name = os.environ.get("EM_WALLET_NAME")
        env_addr = os.environ.get("EM_WALLET_ADDRESS")
        if env_name and env_addr:
            chain_id = int(os.environ.get("EM_CHAIN_ID", str(DEFAULT_CHAIN_ID)))
            return env_name, env_addr, chain_id

        name = profile_name or self.config.active_profile
        profile = self.config.profiles.get(name)
        if not profile:
            return None
        return profile.wallet_name, profile.wallet_address, profile.chain_id

    def get_api_url(self, profile_name: Optional[str] = None) -> str:
        """
        Get API URL with environment variable override.

        Args:
            profile_name: Profile to get URL for (default: active profile)

        Returns:
            API URL
        """
        env_url = os.environ.get("EM_API_URL")
        if env_url:
            return env_url

        # Fall back to config file
        name = profile_name or self.config.active_profile
        profile = self.config.profiles.get(name)
        return profile.api_url if profile else DEFAULT_API_URL

    def get_executor_id(self, profile_name: Optional[str] = None) -> Optional[str]:
        """
        Get executor ID for worker commands.

        Args:
            profile_name: Profile to get ID for (default: active profile)

        Returns:
            Executor ID or None
        """
        env_id = os.environ.get("EM_EXECUTOR_ID")
        if env_id:
            return env_id

        # Fall back to config file
        name = profile_name or self.config.active_profile
        profile = self.config.profiles.get(name)
        return profile.executor_id if profile else None

    def set_profile(
        self,
        name: str,
        wallet_name: str,
        wallet_address: str,
        chain_id: int = DEFAULT_CHAIN_ID,
        api_url: Optional[str] = None,
        executor_id: Optional[str] = None,
        agent_id: Optional[int] = None,
        make_active: bool = True,
    ) -> Profile:
        """
        Create or update a profile bound to an OWS wallet.

        The private key is NEVER stored — only the wallet name (OWS vault key)
        and the EVM address used in the ERC-8128 keyid.
        """
        profile = Profile(
            name=name,
            wallet_name=wallet_name,
            wallet_address=wallet_address,
            chain_id=chain_id,
            api_url=api_url or DEFAULT_API_URL,
            executor_id=executor_id,
            agent_id=agent_id,
        )

        self.config.add_profile(profile)

        if make_active:
            self.config.active_profile = name

        self.save()
        return profile

    def list_profiles(self) -> Dict[str, Profile]:
        """List all profiles."""
        return self.config.profiles

    def delete_profile(self, name: str) -> bool:
        """Delete a profile."""
        success = self.config.remove_profile(name)
        if success:
            self.save()
        return success

    def switch_profile(self, name: str) -> bool:
        """Switch to a different profile."""
        success = self.config.set_active_profile(name)
        if success:
            self.save()
        return success


# Global config manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_wallet() -> Optional[tuple[str, str, int]]:
    """Convenience: (wallet_name, wallet_address, chain_id) or None."""
    return get_config_manager().get_wallet()


def get_api_url() -> str:
    """Convenience function to get API URL."""
    return get_config_manager().get_api_url()


def get_executor_id() -> Optional[str]:
    """Convenience function to get executor ID."""
    return get_config_manager().get_executor_id()

"""
Configuration management for Chamba CLI.

Handles:
- API key storage in ~/.chamba/config
- Environment variable overrides
- Multiple profile support
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict, field


# Default configuration directory
DEFAULT_CONFIG_DIR = Path.home() / ".chamba"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"
DEFAULT_API_URL = "https://api.chamba.ultravioleta.xyz"


@dataclass
class Profile:
    """A Chamba CLI profile configuration."""

    name: str
    api_key: str
    api_url: str = DEFAULT_API_URL
    default_payment_token: str = "USDC"
    default_timeout: float = 30.0
    output_format: str = "table"  # table, json
    executor_id: Optional[str] = None  # For worker profiles

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Profile":
        """Create profile from dictionary."""
        return cls(**data)


@dataclass
class Config:
    """Chamba CLI configuration."""

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
            }
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
            profiles=profiles
        )


class ConfigManager:
    """Manages Chamba CLI configuration."""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize config manager.

        Args:
            config_dir: Custom config directory (default: ~/.chamba)
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
        if os.name != 'nt':  # Not Windows
            self.config_dir.chmod(0o700)

    def load(self) -> Config:
        """Load configuration from file."""
        if not self.config_file.exists():
            return Config()

        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            return Config.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            # Return empty config if file is corrupted
            return Config()

    def save(self) -> None:
        """Save configuration to file."""
        self.ensure_config_dir()

        with open(self.config_file, 'w') as f:
            json.dump(self.config.to_dict(), f, indent=2)

        # Set restrictive permissions on config file
        if os.name != 'nt':  # Not Windows
            self.config_file.chmod(0o600)

    def get_api_key(self, profile_name: Optional[str] = None) -> Optional[str]:
        """
        Get API key with environment variable override.

        Priority:
        1. CHAMBA_API_KEY environment variable
        2. Profile-specific environment variable (CHAMBA_API_KEY_<PROFILE>)
        3. Config file

        Args:
            profile_name: Profile to get key for (default: active profile)

        Returns:
            API key or None
        """
        # Check global env var first
        env_key = os.environ.get("CHAMBA_API_KEY")
        if env_key:
            return env_key

        # Check profile-specific env var
        name = profile_name or self.config.active_profile
        env_key = os.environ.get(f"CHAMBA_API_KEY_{name.upper()}")
        if env_key:
            return env_key

        # Fall back to config file
        profile = self.config.profiles.get(name)
        return profile.api_key if profile else None

    def get_api_url(self, profile_name: Optional[str] = None) -> str:
        """
        Get API URL with environment variable override.

        Args:
            profile_name: Profile to get URL for (default: active profile)

        Returns:
            API URL
        """
        # Check env var first
        env_url = os.environ.get("CHAMBA_API_URL")
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
        # Check env var first
        env_id = os.environ.get("CHAMBA_EXECUTOR_ID")
        if env_id:
            return env_id

        # Fall back to config file
        name = profile_name or self.config.active_profile
        profile = self.config.profiles.get(name)
        return profile.executor_id if profile else None

    def set_profile(
        self,
        name: str,
        api_key: str,
        api_url: Optional[str] = None,
        executor_id: Optional[str] = None,
        make_active: bool = True
    ) -> Profile:
        """
        Create or update a profile.

        Args:
            name: Profile name
            api_key: API key
            api_url: API URL (default: production URL)
            executor_id: Executor ID for worker profiles
            make_active: Make this the active profile

        Returns:
            Created/updated profile
        """
        profile = Profile(
            name=name,
            api_key=api_key,
            api_url=api_url or DEFAULT_API_URL,
            executor_id=executor_id
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


def get_api_key() -> Optional[str]:
    """Convenience function to get API key."""
    return get_config_manager().get_api_key()


def get_api_url() -> str:
    """Convenience function to get API URL."""
    return get_config_manager().get_api_url()


def get_executor_id() -> Optional[str]:
    """Convenience function to get executor ID."""
    return get_config_manager().get_executor_id()

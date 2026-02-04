"""
Enterprise Branding Configuration (NOW-160)

White-label branding support for enterprise customers.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ColorScheme:
    """Brand color scheme."""
    primary: str = "#6366f1"      # Indigo
    secondary: str = "#8b5cf6"    # Purple
    accent: str = "#10b981"       # Emerald
    background: str = "#ffffff"
    surface: str = "#f3f4f6"
    text_primary: str = "#111827"
    text_secondary: str = "#6b7280"
    error: str = "#ef4444"
    success: str = "#22c55e"
    warning: str = "#f59e0b"


@dataclass
class Typography:
    """Brand typography settings."""
    font_family: str = "Inter, system-ui, sans-serif"
    font_family_mono: str = "JetBrains Mono, monospace"
    heading_weight: int = 700
    body_weight: int = 400


@dataclass
class BrandAssets:
    """Brand visual assets."""
    logo_url: Optional[str] = None
    logo_dark_url: Optional[str] = None
    favicon_url: Optional[str] = None
    og_image_url: Optional[str] = None
    app_icon_url: Optional[str] = None


@dataclass
class BrandingConfig:
    """
    Complete branding configuration for white-label deployment.

    Allows enterprises to customize the Execution Market dashboard
    with their own branding.
    """
    # Identity
    org_id: str
    brand_name: str
    tagline: Optional[str] = None

    # Visual identity
    colors: ColorScheme = field(default_factory=ColorScheme)
    typography: Typography = field(default_factory=Typography)
    assets: BrandAssets = field(default_factory=BrandAssets)

    # Domain & URLs
    custom_domain: Optional[str] = None
    support_url: Optional[str] = None
    docs_url: Optional[str] = None
    privacy_url: Optional[str] = None
    terms_url: Optional[str] = None

    # Email
    email_from_name: Optional[str] = None
    email_from_address: Optional[str] = None
    email_template_id: Optional[str] = None

    # Social
    social_links: Dict[str, str] = field(default_factory=dict)

    # Advanced
    custom_css: Optional[str] = None
    custom_js: Optional[str] = None
    hide_powered_by: bool = False

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


def generate_css_variables(config: BrandingConfig) -> str:
    """
    Generate CSS custom properties from branding config.

    Args:
        config: Branding configuration

    Returns:
        CSS string with :root variables
    """
    colors = config.colors
    typography = config.typography

    css = f""":root {{
  /* Colors */
  --color-primary: {colors.primary};
  --color-secondary: {colors.secondary};
  --color-accent: {colors.accent};
  --color-background: {colors.background};
  --color-surface: {colors.surface};
  --color-text-primary: {colors.text_primary};
  --color-text-secondary: {colors.text_secondary};
  --color-error: {colors.error};
  --color-success: {colors.success};
  --color-warning: {colors.warning};

  /* Typography */
  --font-family: {typography.font_family};
  --font-family-mono: {typography.font_family_mono};
  --font-weight-heading: {typography.heading_weight};
  --font-weight-body: {typography.body_weight};

  /* Brand */
  --brand-name: "{config.brand_name}";
}}"""

    if config.custom_css:
        css += f"\n\n/* Custom CSS */\n{config.custom_css}"

    return css


def validate_branding_config(config: BrandingConfig) -> Dict[str, Any]:
    """
    Validate branding configuration.

    Args:
        config: Configuration to validate

    Returns:
        Dict with is_valid and errors
    """
    errors = []

    # Validate colors are valid hex
    color_fields = [
        'primary', 'secondary', 'accent', 'background', 'surface',
        'text_primary', 'text_secondary', 'error', 'success', 'warning'
    ]
    for field in color_fields:
        color = getattr(config.colors, field, None)
        if color and not (color.startswith('#') and len(color) in [4, 7]):
            errors.append(f"Invalid color format for {field}: {color}")

    # Validate URLs
    url_fields = ['logo_url', 'logo_dark_url', 'favicon_url', 'og_image_url']
    for field in url_fields:
        url = getattr(config.assets, field, None)
        if url and not (url.startswith('http://') or url.startswith('https://')):
            errors.append(f"Invalid URL for {field}: {url}")

    # Validate custom domain format
    if config.custom_domain:
        if '/' in config.custom_domain or ':' in config.custom_domain:
            errors.append(f"Custom domain should not include protocol or path: {config.custom_domain}")

    return {
        'is_valid': len(errors) == 0,
        'errors': errors
    }


# Default Execution Market branding
DEFAULT_BRANDING = BrandingConfig(
    org_id="execution-market",
    brand_name="Execution Market",
    tagline="Human Execution Layer for AI Agents",
    colors=ColorScheme(
        primary="#7c3aed",       # Violet
        secondary="#a855f7",     # Purple
        accent="#fbbf24",        # Amber
        background="#0f0f23",    # Dark
        surface="#1a1a2e",       # Dark surface
        text_primary="#ffffff",
        text_secondary="#a1a1aa"
    ),
    assets=BrandAssets(
        logo_url="https://execution.market/logo.svg",
        favicon_url="https://execution.market/favicon.ico"
    ),
    support_url="https://discord.gg/ultravioleta",
    docs_url="https://docs.execution.market"
)

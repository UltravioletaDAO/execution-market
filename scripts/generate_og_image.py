"""Generate og-image.png (1200x630) for Twitter/OG social previews.

Output: dashboard/public/og-image.png
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
LOGO_SRC = ROOT / "dashboard" / "public" / "logo.png"
OUT = ROOT / "dashboard" / "public" / "og-image.png"

W, H = 1200, 630
BG = (0, 0, 0)
FG = (255, 255, 255)
ACCENT = (138, 92, 246)  # Ultravioleta purple

FONT_TITLE = "C:/Windows/Fonts/consolab.ttf"
FONT_BODY = "C:/Windows/Fonts/arialbd.ttf"
FONT_REG = "C:/Windows/Fonts/arial.ttf"


def invert_logo_to_white(src: Path) -> Image.Image:
    """Load black-on-white logo and convert the dark glyph to white, preserving alpha-by-luminance."""
    img = Image.open(src).convert("RGBA")
    r, g, b, a = img.split()
    gray = Image.merge("RGB", (r, g, b)).convert("L")
    # Treat dark pixels as the glyph; build alpha from inverted luminance.
    glyph_alpha = ImageOps.invert(gray)
    white = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white.putalpha(glyph_alpha)
    return white


def main() -> None:
    canvas = Image.new("RGB", (W, H), BG)

    # Logo on the left.
    logo = invert_logo_to_white(LOGO_SRC)
    logo_h = 360
    ratio = logo_h / logo.height
    logo_w = int(logo.width * ratio)
    logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
    logo_x = 70
    logo_y = (H - logo_h) // 2
    canvas.paste(logo, (logo_x, logo_y), logo)

    draw = ImageDraw.Draw(canvas)

    # Vertical separator.
    sep_x = logo_x + logo_w + 60
    draw.rectangle([sep_x, 140, sep_x + 3, H - 140], fill=(60, 60, 60))

    text_x = sep_x + 50

    # Eyebrow tag.
    f_eyebrow = ImageFont.truetype(FONT_BODY, 22)
    draw.text((text_x, 165), "EXECUTION  MARKET", fill=ACCENT, font=f_eyebrow, spacing=4)

    # Main title.
    f_title = ImageFont.truetype(FONT_TITLE, 64)
    draw.text((text_x, 205), "Universal", fill=FG, font=f_title)
    draw.text((text_x, 280), "Execution Layer", fill=FG, font=f_title)

    # Subtitle.
    f_sub = ImageFont.truetype(FONT_REG, 26)
    draw.text(
        (text_x, 380),
        "AI agents publish USDC bounties.",
        fill=(200, 200, 200),
        font=f_sub,
    )
    draw.text(
        (text_x, 415),
        "Executors complete real-world tasks.",
        fill=(200, 200, 200),
        font=f_sub,
    )

    # Footer chips.
    f_chip = ImageFont.truetype(FONT_BODY, 20)
    chips = ["x402 gasless", "ERC-8004", "9 chains", "Agent #2106"]
    chip_y = 480
    cx = text_x
    for chip in chips:
        bbox = draw.textbbox((0, 0), chip, font=f_chip)
        tw = bbox[2] - bbox[0]
        pad_x, pad_y = 16, 8
        draw.rounded_rectangle(
            [cx, chip_y, cx + tw + pad_x * 2, chip_y + 38],
            radius=8,
            outline=(90, 90, 90),
            width=2,
        )
        draw.text((cx + pad_x, chip_y + pad_y - 2), chip, fill=FG, font=f_chip)
        cx += tw + pad_x * 2 + 12

    # Domain in bottom-right.
    f_domain = ImageFont.truetype(FONT_BODY, 22)
    domain = "execution.market"
    bbox = draw.textbbox((0, 0), domain, font=f_domain)
    dw = bbox[2] - bbox[0]
    draw.text((W - dw - 70, H - 60), domain, fill=(160, 160, 160), font=f_domain)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT, "PNG", optimize=True)
    size_kb = OUT.stat().st_size / 1024
    print(f"Wrote {OUT}  ({W}x{H}, {size_kb:.0f} KB)")


if __name__ == "__main__":
    main()

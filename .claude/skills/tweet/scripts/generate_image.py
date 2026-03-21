"""Generate a single image from a text prompt using OpenAI's image generation API."""

import argparse
import base64
import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
    sys.exit(1)


def generate_image(
    prompt: str,
    output_path: str,
    model: str = "gpt-image-1",
    size: str = "1536x1024",
    quality: str = "high",
) -> str:
    """Generate an image from a prompt and save it to output_path."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    print(f"Generating image with {model} ({size})...")
    print(f"Prompt: {prompt[:100]}...")

    result = client.images.generate(
        model=model,
        prompt=prompt,
        n=1,
        size=size,
        quality=quality,
    )

    # gpt-image-1 returns base64 by default
    image_data = result.data[0]

    if hasattr(image_data, "b64_json") and image_data.b64_json:
        img_bytes = base64.b64decode(image_data.b64_json)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img_bytes)
    elif hasattr(image_data, "url") and image_data.url:
        import urllib.request

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(image_data.url, output_path)
    else:
        print("ERROR: No image data in response", file=sys.stderr)
        sys.exit(1)

    file_size = os.path.getsize(output_path)
    print(f"Saved: {output_path} ({file_size / 1024:.0f} KB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate image from text prompt")
    parser.add_argument("--prompt", type=str, help="Direct prompt text")
    parser.add_argument("--prompt-file", type=str, help="Path to .txt file with prompt")
    parser.add_argument("--output", type=str, required=True, help="Output image path")
    parser.add_argument("--model", default="gpt-image-1", help="Model name")
    parser.add_argument("--size", default="1536x1024", help="Image size (e.g. 1536x1024)")
    parser.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    parser.add_argument("--force", action="store_true", help="Overwrite existing file")

    args = parser.parse_args()

    if not args.force and os.path.exists(args.output):
        print(f"SKIP: {args.output} already exists (use --force to overwrite)")
        return

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read().strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        print("ERROR: Provide --prompt or --prompt-file", file=sys.stderr)
        sys.exit(1)

    generate_image(prompt, args.output, model=args.model, size=args.size, quality=args.quality)


if __name__ == "__main__":
    main()

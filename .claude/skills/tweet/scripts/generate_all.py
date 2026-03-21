"""Generate all images for a tweet thread from N.txt prompt files."""

import argparse
import glob
import os
import re
import sys
import time
from pathlib import Path

from generate_image import generate_image


def find_prompt_files(thread_dir: str) -> list[tuple[int, str]]:
    """Find all N.txt files in the thread directory, return sorted (N, path) pairs."""
    pattern = os.path.join(thread_dir, "*.txt")
    results = []
    for path in glob.glob(pattern):
        basename = os.path.basename(path)
        match = re.match(r"^(\d+)\.txt$", basename)
        if match:
            num = int(match.group(1))
            results.append((num, path))
    return sorted(results)


def main():
    parser = argparse.ArgumentParser(description="Generate all images for a thread")
    parser.add_argument("--thread-dir", required=True, help="Path to thread directory")
    parser.add_argument("--model", default="gpt-image-1", help="Model name")
    parser.add_argument("--size", default="1536x1024", help="Image size")
    parser.add_argument("--quality", default="high", choices=["low", "medium", "high"])
    parser.add_argument("--force", action="store_true", help="Regenerate existing images")
    parser.add_argument("--delay", type=float, default=12.0, help="Delay between requests (seconds)")
    parser.add_argument("--start", type=int, default=1, help="Start from prompt N")

    args = parser.parse_args()

    if not os.path.isdir(args.thread_dir):
        print(f"ERROR: Directory not found: {args.thread_dir}", file=sys.stderr)
        sys.exit(1)

    prompts = find_prompt_files(args.thread_dir)
    if not prompts:
        print(f"ERROR: No N.txt prompt files found in {args.thread_dir}", file=sys.stderr)
        sys.exit(1)

    # Filter by start
    prompts = [(n, p) for n, p in prompts if n >= args.start]

    print(f"Found {len(prompts)} prompt files in {args.thread_dir}")
    print(f"Model: {args.model}, Size: {args.size}, Quality: {args.quality}")
    print(f"Delay between requests: {args.delay}s")
    print("---")

    generated = 0
    skipped = 0
    errors = 0

    for i, (num, prompt_path) in enumerate(prompts):
        output_path = os.path.join(args.thread_dir, f"{num}.png")

        if not args.force and os.path.exists(output_path):
            print(f"[{num}] SKIP: {output_path} already exists")
            skipped += 1
            continue

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read().strip()

        print(f"\n[{num}] Generating ({i + 1}/{len(prompts)})...")

        try:
            generate_image(prompt, output_path, model=args.model, size=args.size, quality=args.quality)
            generated += 1
        except Exception as e:
            print(f"[{num}] ERROR: {e}", file=sys.stderr)
            errors += 1

        # Rate limit delay (skip after last image)
        if i < len(prompts) - 1:
            print(f"Waiting {args.delay}s (rate limit)...")
            time.sleep(args.delay)

    print(f"\n--- Done ---")
    print(f"Generated: {generated}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()

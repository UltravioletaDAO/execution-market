#!/usr/bin/env python3
"""
Chamba CLI - Setup script for backwards compatibility.

For modern installations, use pyproject.toml with pip:
    pip install .

This file is kept for compatibility with older tools.
"""

from setuptools import setup, find_packages

# Read version from package
import os
import re

def get_version():
    init_path = os.path.join(os.path.dirname(__file__), "src", "chamba_cli", "__init__.py")
    with open(init_path, "r") as f:
        content = f.read()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if match:
        return match.group(1)
    return "0.1.0"

# Read README for long description
def get_long_description():
    readme_path = os.path.join(os.path.dirname(__file__), "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

setup(
    name="chamba-cli",
    version=get_version(),
    description="Command-line interface for Chamba - Human task execution layer for AI agents",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Ultravioleta DAO",
    author_email="dev@ultravioleta.xyz",
    url="https://github.com/ultravioleta-dao/chamba",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0.0",
        "httpx>=0.24.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "respx>=0.20.0",
            "mypy>=1.0.0",
            "ruff>=0.1.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "chamba = chamba_cli.chamba:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="chamba cli ai-agents human-tasks micropayments x402 ultravioleta",
)

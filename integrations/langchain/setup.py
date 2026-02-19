#!/usr/bin/env python3
"""
Setup script for Execution Market LangChain Integration
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="execution-market-langchain",
    version="1.0.0",
    author="Execution Market",
    author_email="support@execution.market",
    description="LangChain integration for Execution Market - connect AI agents to the physical world",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/execution-market/integrations/langchain",
    py_modules=["em_tools", "em_toolkit"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: LangChain",
    ],
    python_requires=">=3.8",
    install_requires=[
        "langchain-core>=0.1.0",
        "httpx>=0.25.0", 
        "pydantic>=2.0.0",
    ],
    extras_require={
        "agents": ["langchain>=0.1.0"],
        "openai": ["openai>=1.0.0"],
        "anthropic": ["anthropic>=0.20.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0", 
            "black>=23.0.0",
            "isort>=5.0.0",
            "mypy>=1.5.0",
        ],
    },
    keywords="ai, agents, langchain, execution-market, physical-world, tasks, marketplace",
    project_urls={
        "Homepage": "https://execution.market",
        "Documentation": "https://execution.market/docs",
        "Source": "https://github.com/execution-market/integrations",
        "Bug Reports": "https://github.com/execution-market/integrations/issues",
    },
)
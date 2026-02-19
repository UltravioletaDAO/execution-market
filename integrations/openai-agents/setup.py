#!/usr/bin/env python3
"""
Setup configuration for Execution Market OpenAI Agents SDK integration
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Execution Market integration for OpenAI Agents SDK"

# Read requirements from requirements.txt
def read_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            # Filter out comments and empty lines
            requirements = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    requirements.append(line)
            return requirements
    return [
        'openai-agents>=0.2.0',
        'openai>=1.0.0', 
        'requests>=2.28.0',
        'pydantic>=2.0.0',
        'python-dotenv>=0.19.0'
    ]

setup(
    name="execution-market-openai-agents",
    version="1.0.0",
    author="Execution Market",
    author_email="support@execution.market",
    description="OpenAI Agents SDK integration for Execution Market - Agent-to-Human task marketplace",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/execution-market/integrations",
    project_urls={
        "Homepage": "https://execution.market",
        "Documentation": "https://api.execution.market/docs",
        "Dashboard": "https://execution.market/dashboard",
        "Bug Reports": "https://github.com/execution-market/integrations/issues",
    },
    packages=find_packages(exclude=['tests', 'tests.*', 'examples']),
    py_modules=['em_tools', 'em_agent', 'em_swarm'],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers", 
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Office/Business",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9", 
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0", 
            "responses>=0.23.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "mypy>=1.0.0",
        ],
        "examples": [
            "python-dotenv>=0.19.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "em-basic-task=examples.basic_task:main",
            "em-multi-agent=examples.multi_agent:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["README.md", "requirements.txt"],
    },
    keywords=[
        "openai", "agents", "ai", "marketplace", "physical-tasks", 
        "verification", "human-in-the-loop", "task-automation",
        "multi-agent", "swarm", "coordination"
    ],
    zip_safe=False,
)

# Additional setup for development
if __name__ == "__main__":
    print("Execution Market OpenAI Agents Integration")
    print("==========================================")
    print("Setting up the integration package...")
    print()
    print("After installation, you can:")
    print("1. Import agents: from em_agent import TaskManagerAgent")
    print("2. Use tools directly: from em_tools import create_physical_task") 
    print("3. Run swarms: from em_swarm import ExecutionMarketSwarm")
    print("4. Try examples: python examples/basic_task.py")
    print()
    print("Don't forget to set your environment variables:")
    print("- EM_API_KEY (get from https://execution.market/dashboard)")
    print("- OPENAI_API_KEY (get from https://platform.openai.com)")
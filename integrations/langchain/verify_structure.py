#!/usr/bin/env python3
"""
Structure verification script for Execution Market LangChain Integration.
Checks that all files are properly structured without requiring dependencies.
"""

import ast
import sys
from pathlib import Path


def check_python_syntax(file_path):
    """Check if Python file has valid syntax."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


def check_file_structure():
    """Verify all required files exist and have valid syntax."""
    base_dir = Path(__file__).parent
    
    required_files = [
        "em_tools.py",
        "em_toolkit.py", 
        "__init__.py",
        "README.md",
        "requirements.txt",
        "setup.py",
        "examples/simple_task.py",
        "examples/agent_with_em.py",
    ]
    
    print("🔍 Verifying file structure...")
    
    all_good = True
    for file_path in required_files:
        full_path = base_dir / file_path
        
        if not full_path.exists():
            print(f"❌ Missing: {file_path}")
            all_good = False
            continue
            
        print(f"✅ Found: {file_path}")
        
        # Check Python files for syntax
        if file_path.endswith('.py'):
            valid, error = check_python_syntax(full_path)
            if not valid:
                print(f"❌ Syntax error in {file_path}: {error}")
                all_good = False
            else:
                print(f"   ✅ Valid Python syntax")
    
    return all_good


def check_imports():
    """Check that imports are structured correctly (without actually importing)."""
    print("\n🔍 Checking import structure...")
    
    base_dir = Path(__file__).parent
    
    # Check em_tools.py
    tools_file = base_dir / "em_tools.py"
    with open(tools_file, 'r') as f:
        tools_content = f.read()
        
    expected_tools = [
        "CreatePhysicalTaskTool",
        "CheckTaskStatusTool", 
        "ListMyTasksTool",
        "ApproveSubmissionTool",
        "SearchTasksTool"
    ]
    
    for tool in expected_tools:
        if f"class {tool}" in tools_content:
            print(f"✅ Tool class found: {tool}")
        else:
            print(f"❌ Tool class missing: {tool}")
            
    # Check toolkit file
    toolkit_file = base_dir / "em_toolkit.py"
    with open(toolkit_file, 'r') as f:
        toolkit_content = f.read()
        
    expected_toolkits = [
        "ExecutionMarketToolkit",
        "ExecutionMarketAgentToolkit",
        "ExecutionMarketWorkerToolkit"
    ]
    
    for toolkit in expected_toolkits:
        if f"class {toolkit}" in toolkit_content:
            print(f"✅ Toolkit class found: {toolkit}")
        else:
            print(f"❌ Toolkit class missing: {toolkit}")


def check_documentation():
    """Check that documentation is comprehensive."""
    print("\n🔍 Checking documentation...")
    
    base_dir = Path(__file__).parent
    readme_file = base_dir / "README.md"
    
    with open(readme_file, 'r') as f:
        readme_content = f.read()
    
    required_sections = [
        "Quick Start",
        "Installation", 
        "Available Tools",
        "Task Categories",
        "Evidence Types",
        "Authentication",
        "Examples"
    ]
    
    for section in required_sections:
        if section.lower() in readme_content.lower():
            print(f"✅ Documentation section: {section}")
        else:
            print(f"⚠️ Documentation section missing or unclear: {section}")


def main():
    """Run all verification checks."""
    print("🌍 Execution Market LangChain Integration - Structure Verification")
    print("=" * 70)
    
    # Check file structure and syntax
    structure_ok = check_file_structure()
    
    # Check imports
    check_imports()
    
    # Check documentation
    check_documentation()
    
    print("\n" + "=" * 70)
    
    if structure_ok:
        print("✅ All structure checks passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Test with real LLM: python examples/simple_task.py")
        print("3. Integrate with your LangChain agent")
        return 0
    else:
        print("❌ Some structure issues found. Please fix before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
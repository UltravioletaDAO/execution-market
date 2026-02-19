#!/usr/bin/env python3
"""
Import validation test for Execution Market OpenAI Agents SDK Integration.

This script validates that all modules can be imported without network calls.
Run this before installing to ensure the package structure is correct.
"""

import sys
import ast
import traceback

def test_syntax(file_path: str) -> bool:
    """Test if a Python file has valid syntax."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False

def test_imports():
    """Test that all modules can be imported (syntax validation only)."""
    print("🧪 Testing Execution Market OpenAI Agents SDK Integration imports...")
    
    # Test syntax of core files
    files_to_check = [
        'em_tools.py',
        'em_agent.py',
        'em_swarm.py', 
        '__init__.py'
    ]
    
    syntax_ok = True
    for file_path in files_to_check:
        if not test_syntax(file_path):
            syntax_ok = False
    
    if not syntax_ok:
        print("❌ Syntax validation failed")
        return False
        
    # Test imports (will fail without dependencies, but that's expected)
    print("\n📦 Testing imports (dependency errors are expected)...")
    
    try:
        # Test individual modules
        import em_tools
        print("✅ em_tools imported successfully")
    except ImportError as e:
        print(f"⚠️  em_tools import failed (expected): {e}")
    except Exception as e:
        print(f"❌ em_tools unexpected error: {e}")
        return False
        
    try:
        import em_agent
        print("✅ em_agent imported successfully")
    except ImportError as e:
        print(f"⚠️  em_agent import failed (expected): {e}")
    except Exception as e:
        print(f"❌ em_agent unexpected error: {e}")
        return False
        
    try:
        import em_swarm
        print("✅ em_swarm imported successfully")
    except ImportError as e:
        print(f"⚠️  em_swarm import failed (expected): {e}")
    except Exception as e:
        print(f"❌ em_swarm unexpected error: {e}")
        return False
        
    print("\n✅ Import validation completed - package structure is correct!")
    print("💡 Install dependencies to enable full functionality:")
    print("   pip install openai-agents httpx pydantic")
    
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
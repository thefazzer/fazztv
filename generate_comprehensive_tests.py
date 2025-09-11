#!/usr/bin/env python3
"""
Comprehensive test generation script for achieving 100% code coverage.
This script generates unit tests for all modules in the fazztv package.
"""

import os
import ast
import textwrap
from pathlib import Path
from typing import List, Dict, Set, Tuple
import subprocess
import sys


class TestGenerator:
    """Generate comprehensive unit tests for Python modules."""
    
    def __init__(self, module_path: str, test_dir: str = "tests/unit"):
        self.module_path = Path(module_path)
        self.test_dir = Path(test_dir)
        self.test_dir.mkdir(parents=True, exist_ok=True)
    
    def analyze_module(self, file_path: Path) -> Dict:
        """Analyze a Python module to identify testable components."""
        with open(file_path, 'r') as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                return {}
        
        analysis = {
            'classes': [],
            'functions': [],
            'imports': [],
            'constants': []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                analysis['classes'].append({
                    'name': node.name,
                    'methods': methods
                })
            elif isinstance(node, ast.FunctionDef):
                # Top-level functions only
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                    analysis['functions'].append(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis['imports'].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    analysis['imports'].append(node.module)
        
        return analysis
    
    def generate_test_cases(self, module_name: str, analysis: Dict) -> str:
        """Generate test cases based on module analysis."""
        test_content = [
            '"""Comprehensive unit tests for {} module."""'.format(module_name),
            '',
            'import pytest',
            'import os',
            'import sys',
            'from unittest.mock import Mock, patch, MagicMock, call',
            'from pathlib import Path',
            'import tempfile',
            '',
        ]
        
        # Import the module being tested
        module_import = module_name.replace('/', '.').replace('.py', '')
        if 'fazztv' in module_import:
            test_content.append(f'from {module_import} import *')
        test_content.append('')
        
        # Generate class tests
        for cls in analysis['classes']:
            test_content.append(f'class Test{cls["name"]}:')
            test_content.append(f'    """Test the {cls["name"]} class."""')
            test_content.append('')
            
            # Generate test for each method
            for method in cls['methods']:
                if method.startswith('_'):
                    continue  # Skip private methods for now
                
                test_content.append(f'    def test_{method}(self):')
                test_content.append(f'        """Test {method} method."""')
                test_content.append(f'        # TODO: Implement test for {method}')
                test_content.append(f'        pass')
                test_content.append('')
            
            # Add edge case tests
            test_content.append(f'    def test_{cls["name"].lower()}_edge_cases(self):')
            test_content.append(f'        """Test edge cases for {cls["name"]}."""')
            test_content.append(f'        # TODO: Implement edge case tests')
            test_content.append(f'        pass')
            test_content.append('')
            test_content.append('')
        
        # Generate function tests
        if analysis['functions']:
            test_content.append('class TestModuleFunctions:')
            test_content.append('    """Test module-level functions."""')
            test_content.append('')
            
            for func in analysis['functions']:
                if func.startswith('_'):
                    continue
                
                test_content.append(f'    def test_{func}(self):')
                test_content.append(f'        """Test {func} function."""')
                test_content.append(f'        # TODO: Implement test for {func}')
                test_content.append(f'        pass')
                test_content.append('')
            
            test_content.append('')
        
        # Generate integration tests
        test_content.append('class TestIntegration:')
        test_content.append('    """Integration tests for the module."""')
        test_content.append('')
        test_content.append('    def test_module_imports(self):')
        test_content.append('        """Test that all imports work correctly."""')
        test_content.append('        # TODO: Verify imports')
        test_content.append('        pass')
        test_content.append('')
        test_content.append('    def test_error_handling(self):')
        test_content.append('        """Test error handling throughout the module."""')
        test_content.append('        # TODO: Test error scenarios')
        test_content.append('        pass')
        test_content.append('')
        
        return '\n'.join(test_content)
    
    def generate_tests_for_module(self, module_file: Path) -> bool:
        """Generate tests for a single module."""
        # Skip __pycache__ and non-Python files
        if '__pycache__' in str(module_file) or not module_file.suffix == '.py':
            return False
        
        # Skip __init__.py files
        if module_file.name == '__init__.py':
            return False
        
        # Determine test file name
        relative_path = module_file.relative_to(self.module_path)
        test_file_name = f'test_{relative_path.stem}_auto.py'
        test_file_path = self.test_dir / test_file_name
        
        # Skip if test already exists
        if test_file_path.exists():
            return False
        
        # Analyze module
        analysis = self.analyze_module(module_file)
        if not analysis or (not analysis['classes'] and not analysis['functions']):
            return False
        
        # Generate test content
        module_name = str(relative_path).replace('/', '.').replace('.py', '')
        module_name = f'fazztv.{module_name}'
        test_content = self.generate_test_cases(module_name, analysis)
        
        # Write test file
        with open(test_file_path, 'w') as f:
            f.write(test_content)
        
        print(f"Generated test: {test_file_path}")
        return True
    
    def generate_all_tests(self) -> int:
        """Generate tests for all modules in the package."""
        generated_count = 0
        
        for py_file in self.module_path.rglob('*.py'):
            if self.generate_tests_for_module(py_file):
                generated_count += 1
        
        return generated_count


def get_coverage_report() -> Dict[str, float]:
    """Get current test coverage for each module."""
    result = subprocess.run(
        ['pytest', '--cov=fazztv', '--cov-report=json', '--tb=no', '-q', 'tests/unit'],
        capture_output=True,
        text=True
    )
    
    coverage = {}
    if result.returncode == 0:
        import json
        try:
            with open('coverage.json', 'r') as f:
                data = json.load(f)
                for file_path, file_data in data.get('files', {}).items():
                    if 'fazztv' in file_path:
                        coverage[file_path] = file_data.get('summary', {}).get('percent_covered', 0)
        except:
            pass
    
    return coverage


def prioritize_modules(coverage: Dict[str, float]) -> List[str]:
    """Prioritize modules by lowest coverage first."""
    return sorted(coverage.items(), key=lambda x: x[1])


def main():
    """Main execution function."""
    print("FazzTV Comprehensive Test Generator")
    print("=" * 50)
    
    # Generate tests
    generator = TestGenerator('fazztv', 'tests/unit')
    count = generator.generate_all_tests()
    
    print(f"\nGenerated {count} new test files")
    
    # Get coverage report
    print("\nGetting current coverage report...")
    coverage = get_coverage_report()
    
    if coverage:
        print("\nModules with lowest coverage:")
        for module, cov in prioritize_modules(coverage)[:10]:
            print(f"  {module}: {cov:.1f}%")
    
    print("\nRecommendations:")
    print("1. Review and complete the TODO sections in generated tests")
    print("2. Focus on modules with lowest coverage first")
    print("3. Add edge cases and error handling tests")
    print("4. Run 'pytest --cov=fazztv --cov-report=html' for detailed coverage")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
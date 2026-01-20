"""
Phase 2: Static analysis for code smells and security issues.
"""

import ast
import subprocess
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from janitor.config import Config, AnalyzerConfig


@dataclass
class AnalysisResult:
    """Result from static analysis."""
    has_issues: bool
    issue_count: int
    issues_by_severity: Dict[str, List[Dict]] = field(default_factory=dict)
    issues_by_type: Dict[str, List[Dict]] = field(default_factory=dict)
    complexity_metrics: Dict[str, Any] = field(default_factory=dict)
    security_issues: List[Dict] = field(default_factory=list)
    code_smells: List[Dict] = field(default_factory=list)
    radon_complexity: Dict[str, Any] = field(default_factory=dict)


class Analyzer:
    """Main static analysis interface."""
    
    def __init__(self, config: Config):
        """Initialize analyzer with configuration."""
        self.config = config
        self.analyzer_config = config.analyzer
        self.logger = logging.getLogger(__name__)
        self.issues: List[Dict] = []
    
    def analyze(self, target: Path) -> AnalysisResult:
        """Run static analysis on target."""
        if target.is_file():
            return self._analyze_file(target)
        if target.is_dir():
            return self._analyze_directory(target)
        return AnalysisResult(
            has_issues=False,
            issue_count=0,
            issues_by_severity={"error": [], "warning": [], "info": []},
            issues_by_type={"security": [], "complexity": [], "maintainability": []}
        )
    
    def _analyze_file(self, file_path: Path) -> AnalysisResult:
        """Analyze a single file."""
        self.issues = []
        suffix = file_path.suffix.lower()
        
        if suffix == '.py':
            return self._analyze_python_file(file_path)
        if suffix in {'.js', '.ts', '.jsx', '.tsx'}:
            return self._analyze_js_file(file_path)
        return AnalysisResult(
            has_issues=False,
            issue_count=0
        )
    
    def _analyze_python_file(self, file_path: Path) -> AnalysisResult:
        """Perform detailed analysis of Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except OSError as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            return AnalysisResult(
                has_issues=True,
                issue_count=1,
                issues_by_severity={"error": [{
                    "file": str(file_path),
                    "message": f"Read error: {e}",
                    "line": 1,
                    "type": "io"
                }]}
            )
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            self.logger.error(f"Syntax error in {file_path}: {e}")
            return AnalysisResult(
                has_issues=True,
                issue_count=1,
                issues_by_severity={"error": [{
                    "file": str(file_path),
                    "message": f"Syntax error: {e.msg}",
                    "line": e.lineno or 1,
                    "type": "syntax"
                }]},
                issues_by_type={"syntax": []}
            )
        
        self._detect_deep_nesting(tree, file_path)
        self._detect_long_functions(tree, file_path)
        self._detect_dead_code(tree, content, file_path)
        self._detect_security_issues(tree, file_path)
        
        radon_data = self._analyze_with_radon(file_path)
        if radon_data:
            self._detect_complexity_from_radon(radon_data, file_path)
        
        self._analyze_with_bandit(file_path)
        
        result = AnalysisResult(
            has_issues=len(self.issues) > 0,
            issue_count=len(self.issues),
            security_issues=[i for i in self.issues if i.get('type') == 'security'],
            code_smells=[i for i in self.issues if i.get('type') != 'security'],
            radon_complexity=radon_data or {}
        )
        
        for issue in self.issues:
            severity = issue.get('severity', 'warning')
            result.issues_by_severity.setdefault(severity, []).append(issue)
            
            category = issue.get('type', 'maintainability')
            result.issues_by_type.setdefault(category, []).append(issue)
        
        return result
    
    def _detect_deep_nesting(self, tree: ast.AST, file_path: Path) -> None:
        """Detect excessive nesting in control flow structures."""
        max_depth = self.analyzer_config.max_nesting_depth
        
        class NestingAnalyzer(ast.NodeVisitor):
            __slots__ = ('current_depth', 'violations', 'max_depth')
            
            def __init__(self, max_depth: int):
                self.current_depth = 0
                self.violations = []
                self.max_depth = max_depth
            
            def _check_nesting(self, node: ast.AST, node_type: str) -> None:
                self.current_depth += 1
                if self.current_depth > self.max_depth:
                    self.violations.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "message": f"Deep nesting in {node_type} (depth: {self.current_depth})",
                        "type": "maintainability",
                        "severity": "warning",
                        "suggestion": "Consider extracting into helper functions or using early returns"
                    })
                self.generic_visit(node)
                self.current_depth -= 1
            
            def visit_If(self, node: ast.AST) -> None:
                self._check_nesting(node, "if block")
            
            def visit_For(self, node: ast.AST) -> None:
                self._check_nesting(node, "for loop")
            
            def visit_While(self, node: ast.AST) -> None:
                self._check_nesting(node, "while loop")
            
            def visit_Try(self, node: ast.AST) -> None:
                self._check_nesting(node, "try block")
        
        analyzer = NestingAnalyzer(max_depth)
        analyzer.visit(tree)
        self.issues.extend(analyzer.violations)
    
    def _detect_long_functions(self, tree: ast.AST, file_path: Path) -> None:
        """Detect functions that exceed length thresholds."""
        max_lines = self.analyzer_config.max_function_lines
        
        class LengthAnalyzer(ast.NodeVisitor):
            __slots__ = ('violations', 'max_lines')
            
            def __init__(self, max_lines: int):
                self.violations = []
                self.max_lines = max_lines
            
            def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                end_line = node.end_lineno or node.lineno
                length = end_line - node.lineno + 1
                
                if length > self.max_lines:
                    self.violations.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "message": f"Function '{node.name}' is {length} lines (max: {self.max_lines})",
                        "type": "maintainability",
                        "severity": "warning",
                        "suggestion": "Consider breaking into smaller helper functions",
                        "function_name": node.name,
                        "function_length": length
                    })
                self.generic_visit(node)
            
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._check_function(node)
            
            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._check_function(node)
        
        analyzer = LengthAnalyzer(max_lines)
        analyzer.visit(tree)
        self.issues.extend(analyzer.violations)
    
    def _detect_dead_code(self, tree: ast.AST, content: str, 
                          file_path: Path) -> None:
        """Detect unused variables, unreachable code, and dead functions."""
        
        class SymbolCollector(ast.NodeVisitor):
            __slots__ = ('defined_names', 'used_names', 'assignments', 'usages')
            
            def __init__(self):
                self.defined_names = set()
                self.used_names = set()
                self.assignments = {}
                self.usages = {}
            
            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self.defined_names.add(node.name)
                self.assignments[node.name] = node.lineno
                self.generic_visit(node)
            
            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self.visit_FunctionDef(node)
            
            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                self.defined_names.add(node.name)
                self.assignments[node.name] = node.lineno
                self.generic_visit(node)
            
            def visit_Name(self, node: ast.Name) -> None:
                if isinstance(node.ctx, ast.Store):
                    self.defined_names.add(node.id)
                    self.assignments[node.id] = node.lineno
                elif isinstance(node.ctx, ast.Load):
                    self.used_names.add(node.id)
        
        collector = SymbolCollector()
        collector.visit(tree)
        
        unused = collector.defined_names - collector.used_names
        
        for name in unused:
            if name in collector.assignments:
                self.issues.append({
                    "file": str(file_path),
                    "line": collector.assignments[name],
                    "message": f"Variable or function '{name}' is defined but never used",
                    "type": "maintainability",
                    "severity": "info",
                    "suggestion": "Remove unused definition or ensure it's called"
                })
    
    def _detect_security_issues(self, tree: ast.AST, file_path: Path) -> None:
        """Detect common security vulnerabilities."""
        
        class SecurityAnalyzer(ast.NodeVisitor):
            __slots__ = ('violations',)
            
            def __init__(self):
                self.violations = []
            
            def visit_Call(self, node: ast.Call) -> None:
                if isinstance(node.func, ast.Name):
                    if node.func.id in ('eval', 'exec'):
                        self.violations.append({
                            "file": str(file_path),
                            "line": node.lineno,
                            "message": "Dangerous use of eval/exec detected",
                            "type": "security",
                            "severity": "critical",
                            "suggestion": "Avoid eval/exec with user input"
                        })
                
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == 'execute':
                        for arg in node.args:
                            if isinstance(arg, (ast.BinOp, ast.Mod)):
                                self.violations.append({
                                    "file": str(file_path),
                                    "line": node.lineno,
                                    "message": "Potential SQL injection - use parameterized queries",
                                    "type": "security",
                                    "severity": "critical"
                                })
                
                self.generic_visit(node)
            
            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    if alias.name in ('pickle', 'cPickle'):
                        self.violations.append({
                            "file": str(file_path),
                            "line": node.lineno,
                            "message": "pickle module can execute arbitrary code",
                            "type": "security",
                            "severity": "warning",
                            "suggestion": "Consider safer alternatives like json"
                        })
                self.generic_visit(node)
            
            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                if node.module in ('pickle', 'cPickle'):
                    self.violations.append({
                        "file": str(file_path),
                        "line": node.lineno,
                        "message": "pickle module can execute arbitrary code",
                        "type": "security",
                        "severity": "warning"
                    })
                self.generic_visit(node)
        
        analyzer = SecurityAnalyzer()
        analyzer.visit(tree)
        self.issues.extend(analyzer.violations)
    
    def _analyze_with_radon(self, file_path: Path) -> Dict[str, Any]:
        """Run Radon complexity analysis on Python file."""
        try:
            result = subprocess.run(
                ["radon", "cc", str(file_path), "-a", "-j"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                if result.stderr:
                    self.logger.warning(f"Radon warning: {result.stderr.strip()}")
                return {}
            
            if not result.stdout:
                return {}
            
            try:
                data = json.loads(result.stdout)
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list) and value:
                            func_dict = {}
                            for func in value:
                                if isinstance(func, dict) and 'name' in func:
                                    func_dict[func['name']] = func
                            return func_dict
                        if isinstance(value, dict):
                            return value
                
                return data if isinstance(data, dict) else {}
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse Radon output for {file_path}: {e}")
                return {}
            
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Radon analysis timed out for {file_path}")
        except FileNotFoundError:
            self.logger.warning("Radon not installed. Run: pip install radon")
        except OSError as e:
            self.logger.warning(f"Radon analysis failed: {e}")
        
        return {}
    
    def _detect_complexity_from_radon(self, radon_data: Dict[str, Any], 
                                       file_path: Path) -> None:
        """Process Radon complexity data and add issues."""
        max_complexity = self.analyzer_config.max_cyclomatic_complexity
        max_lines = self.analyzer_config.max_function_lines
        
        if not radon_data or not isinstance(radon_data, dict):
            return
            
        for func_name, details in radon_data.items():
            if not isinstance(details, dict):
                continue
            
            score = details.get('complexity', 0)
            loc = details.get('loc', 0)
            
            if score > max_complexity:
                self.issues.append({
                    "file": str(file_path),
                    "line": details.get('start_line', 1),
                    "message": f"High Complexity: '{func_name}' has score {score}",
                    "type": "complexity",
                    "severity": "warning",
                    "suggestion": "Consider breaking into smaller functions",
                    "complexity": score
                })
            
            if loc > max_lines:
                self.issues.append({
                    "file": str(file_path),
                    "line": details.get('start_line', 1),
                    "message": f"Long Function: '{func_name}' is {loc} lines (max: {max_lines})",
                    "type": "maintainability",
                    "severity": "warning",
                    "suggestion": "Consider extracting into helper functions",
                    "function_length": loc
                })
    
    def _analyze_with_bandit(self, file_path: Path) -> None:
        """Run Bandit security analysis on Python file."""
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if not result.stdout:
                return
            
            try:
                bandit_data = json.loads(result.stdout)
                results = bandit_data.get("results", [])
                
                for issue in results:
                    self.issues.append({
                        "file": str(file_path),
                        "line": issue.get('line_number', 1),
                        "message": issue.get('issue_text', 'Security issue detected'),
                        "type": "security",
                        "severity": issue.get('issue_severity', 'warning'),
                        "suggestion": issue.get('issue_text', ''),
                        "confidence": issue.get('issue_confidence', 'medium'),
                        "test_name": issue.get('test_name', '')
                    })
                    
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse Bandit output for {file_path}: {e}")
                    
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Bandit analysis timed out for {file_path}")
        except FileNotFoundError:
            self.logger.warning("Bandit not installed. Run: pip install bandit")
        except OSError as e:
            self.logger.warning(f"Bandit analysis failed: {e}")
    
    def _analyze_directory(self, dir_path: Path) -> AnalysisResult:
        """Analyze all files in a directory."""
        all_issues = []
        
        for code_file in self._collect_code_files(dir_path):
            result = self._analyze_file(code_file)
            all_issues.extend(result.code_smells)
            all_issues.extend(result.security_issues)
        
        return AnalysisResult(
            has_issues=len(all_issues) > 0,
            issue_count=len(all_issues),
            security_issues=[i for i in all_issues if i.get('type') == 'security'],
            code_smells=[i for i in all_issues if i.get('type') != 'security']
        )
    
    def _collect_code_files(self, dir_path: Path) -> List[Path]:
        """Collect all code files in directory."""
        code_files = []
        for ext in ['*.py', '*.js', '*.ts']:
            code_files.extend(dir_path.rglob(ext))
        return code_files
    
    def _analyze_js_file(self, file_path: Path) -> AnalysisResult:
        """Placeholder for JavaScript/TypeScript analysis."""
        return AnalysisResult(
            has_issues=False,
            issue_count=0
        )

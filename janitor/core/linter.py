"""
Phase 1: Linting and formatting implementation.
"""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from janitor.config import Config, LinterConfig


@dataclass
class LintResult:
    """Result from linting operation."""
    success: bool
    has_issues: bool
    issues: List[Dict[str, Any]]
    auto_fixed: List[Dict[str, Any]]
    formatted_code: Optional[str] = None
    raw_output: str = ""


class Linter:
    """Main linting interface supporting multiple linting backends."""
    
    def __init__(self, config: Config):
        """Initialize linter with configuration."""
        self.config = config
        self.linter_config = config.linter
        self.logger = logging.getLogger(__name__)
    
    def analyze(self, target: Path, auto_fix: bool = True) -> LintResult:
        """Analyze code for linting issues."""
        if target.is_file() and self._is_code_file(target):
            return self._lint_file(target, auto_fix)
        if target.is_dir():
            return self._lint_directory(target, auto_fix)
        return LintResult(
            success=False,
            has_issues=False,
            issues=[{"error": f"Invalid target: {target}"}],
            auto_fixed=[]
        )
    
    def _is_code_file(self, path: Path) -> bool:
        """Check if file is a code file worth linting."""
        code_extensions = {'.py', '.pyw', '.js', '.ts', '.jsx', '.tsx'}
        return path.suffix.lower() in code_extensions
    
    def _lint_file(self, file_path: Path, auto_fix: bool) -> LintResult:
        """Lint a single file."""
        suffix = file_path.suffix.lower()
        
        if suffix == '.py':
            return self._lint_with_ruff(file_path, auto_fix)
        
        return self._generic_lint(file_path)
    
    def _lint_with_ruff(self, file_path: Path, auto_fix: bool) -> LintResult:
        """Lint Python file using Ruff."""
        try:
            result = subprocess.run(
                ['ruff', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                self.logger.warning("Ruff not found, using generic linting")
                return self._generic_lint(file_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.logger.warning("Ruff not installed, falling back to generic")
            return self._generic_lint(file_path)
        except OSError as e:
            self.logger.warning(f"Ruff check failed: {e}")
            return self._generic_lint(file_path)
        
        cmd = ['ruff', 'check', str(file_path), '--format=text']
        if auto_fix:
            cmd.append('--fix')
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            issues = self._parse_ruff_output(result.stdout, result.stderr)
            auto_fixed = []
            
            if auto_fix and result.returncode == 0:
                format_result = subprocess.run(
                    ['ruff', 'format', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if format_result.returncode == 0:
                    auto_fixed.append({
                        "tool": "ruff",
                        "type": "formatting",
                        "description": "Auto-formatted with Ruff"
                    })
            
            return LintResult(
                success=result.returncode == 0,
                has_issues=len(issues) > 0 or len(auto_fixed) > 0,
                issues=issues,
                auto_fixed=auto_fixed,
                raw_output=f"{result.stdout}\n{result.stderr}"
            )
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Linting timed out for {file_path}")
            return LintResult(
                success=False,
                has_issues=False,
                issues=[{"error": "Linting timeout"}],
                auto_fixed=[]
            )
        except OSError as e:
            self.logger.error(f"Linting failed: {e}")
            return LintResult(
                success=False,
                has_issues=False,
                issues=[{"error": str(e)}],
                auto_fixed=[]
            )
    
    def _parse_ruff_output(self, stdout: str, stderr: str) -> List[Dict[str, Any]]:
        """Parse Ruff output into structured issues."""
        issues = []
        lines = stdout.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            parts = line.split(':')
            if len(parts) >= 4:
                try:
                    issue = {
                        "file": parts[0],
                        "line": int(parts[1]),
                        "column": int(parts[2]),
                        "message": ':'.join(parts[3:]).strip(),
                        "tool": "ruff"
                    }
                    issues.append(issue)
                except (ValueError, IndexError):
                    if "error" not in line.lower():
                        issues.append({"raw": line})
        
        return issues
    
    def _lint_directory(self, dir_path: Path, auto_fix: bool) -> LintResult:
        """Lint all code files in a directory."""
        all_issues = []
        all_auto_fixed = []
        
        for code_file in self._collect_code_files(dir_path):
            result = self._lint_file(code_file, auto_fix)
            all_issues.extend(result.issues)
            all_auto_fixed.extend(result.auto_fixed)
        
        return LintResult(
            success=len(all_issues) == 0,
            has_issues=len(all_issues) > 0 or len(all_auto_fixed) > 0,
            issues=all_issues,
            auto_fixed=all_auto_fixed
        )
    
    def _collect_code_files(self, dir_path: Path) -> List[Path]:
        """Collect all code files in directory recursively."""
        code_files = []
        for ext in ['*.py', '*.js', '*.ts', '*.jsx', '*.tsx']:
            code_files.extend(dir_path.rglob(ext))
        return code_files
    
    def _generic_lint(self, file_path: Path) -> LintResult:
        """Generic fallback linting using AST analysis."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
        except OSError as e:
            return LintResult(
                success=False,
                has_issues=False,
                issues=[{"error": str(e)}],
                auto_fixed=[]
            )
        
        issues = []
        max_len = self.linter_config.max_line_length
        
        for i, line in enumerate(lines, 1):
            if len(line) > max_len:
                issues.append({
                    "file": str(file_path),
                    "line": i,
                    "column": max_len,
                    "message": f"Line exceeds {max_len} characters",
                    "tool": "generic",
                    "severity": "warning"
                })
            
            stripped = line.rstrip()
            if stripped != line:
                issues.append({
                    "file": str(file_path),
                    "line": i,
                    "message": "Trailing whitespace",
                    "tool": "generic",
                    "severity": "info"
                })
        
        if content and not content.endswith('\n'):
            issues.append({
                "file": str(file_path),
                "line": len(lines),
                "message": "No newline at end of file",
                "tool": "generic",
                "severity": "info"
            })
        
        return LintResult(
            success=True,
            has_issues=len(issues) > 0,
            issues=issues,
            auto_fixed=[],
            raw_output=f"Found {len(issues)} issues"
        )

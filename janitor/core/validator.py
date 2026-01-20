"""
Validation and self-healing loop for AI refactoring.
"""

import subprocess
import tempfile
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import re

from janitor.config import Config
from janitor.core.refactorer import RefactorResult
from janitor.core.linter import Linter


@dataclass
class ValidationResult:
    """Result from validation."""
    passed: bool
    checks: List[Dict[str, Any]]
    error: Optional[str] = None


class Validator:
    """Validates refactored code before applying changes."""
    
    def __init__(self, config: Config):
        """Initialize validator with configuration."""
        self.config = config
        self.validator_config = config.validator
        self.logger = logging.getLogger(__name__)
        self.temp_dir: Optional[Path] = None
    
    def validate(self, refactor_result: RefactorResult) -> bool:
        """Validate refactored code."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="janitor_"))
        
        try:
            temp_file = self.temp_dir / "refactored.py"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(refactor_result.refactored_code)
            
            checks = []
            
            syntax_check = self._check_syntax(temp_file)
            checks.append(syntax_check)
            
            if not syntax_check['passed']:
                return False
            
            if self.validator_config.run_linter_after:
                lint_check = self._check_linting(temp_file)
                checks.append(lint_check)
            
            if self.validator_config.run_static_analysis:
                analysis_check = self._check_static_analysis(temp_file)
                checks.append(analysis_check)
            
            safety_check = self._check_safety_rules(temp_file)
            checks.append(safety_check)
            
            passed = all(check['passed'] for check in checks)
            
            if not passed:
                self.logger.warning("Validation failed checks:")
                for check in checks:
                    if not check.get('passed', True):
                        self.logger.warning(f"  - {check.get('message', 'Unknown check')}")
            
            return passed
            
        finally:
            if self.temp_dir and self.temp_dir.exists():
                try:
                    shutil.rmtree(self.temp_dir)
                except OSError:
                    pass
                self.temp_dir = None
    
    def apply_changes(self, refactor_result: RefactorResult) -> None:
        """Apply validated refactored code."""
        self.logger.info("Changes validated and ready to apply")
    
    def _check_syntax(self, file_path: Path) -> Dict[str, Any]:
        """Check Python syntax validity."""
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            compile(code, file_path, 'exec')
            
            return {
                "passed": True,
                "check": "syntax",
                "message": "Syntax is valid"
            }
        except SyntaxError as e:
            return {
                "passed": False,
                "check": "syntax",
                "message": f"Syntax error: {e.msg}",
                "error": str(e)
            }
        except OSError as e:
            return {
                "passed": False,
                "check": "syntax",
                "message": f"Syntax check failed: {e}",
                "error": str(e)
            }
    
    def _check_linting(self, file_path: Path) -> Dict[str, Any]:
        """Run linter on refactored code."""
        try:
            linter = Linter(self.config)
            result = linter.analyze(file_path, auto_fix=False)
            
            if result.has_issues:
                return {
                    "passed": False,
                    "check": "linting",
                    "message": f"Found {len(result.issues)} linting issues",
                    "issues": result.issues
                }
            
            return {
                "passed": True,
                "check": "linting",
                "message": "No linting issues"
            }
        except Exception as e:
            return {
                "passed": False,
                "check": "linting",
                "message": f"Linting check failed: {e}",
                "error": str(e)
            }
    
    def _check_static_analysis(self, file_path: Path) -> Dict[str, Any]:
        """Run static analysis on refactored code."""
        from janitor.core.analyzer import Analyzer
        
        try:
            analyzer = Analyzer(self.config)
            result = analyzer.analyze(file_path)
            
            critical_issues = [
                i for i in result.security_issues 
                if i.get('severity') == 'critical'
            ]
            
            if critical_issues:
                return {
                    "passed": False,
                    "check": "static_analysis",
                    "message": f"Found {len(critical_issues)} critical security issues",
                    "issues": critical_issues
                }
            
            return {
                "passed": True,
                "check": "static_analysis",
                "message": "Static analysis passed"
            }
        except Exception as e:
            return {
                "passed": False,
                "check": "static_analysis",
                "message": f"Static analysis check failed: {e}",
                "error": str(e)
            }
    
    def _check_safety_rules(self, file_path: Path) -> Dict[str, Any]:
        """Check against safety rules for AI-generated code."""
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            if self._contains_hardcoded_secrets(code):
                return {
                    "passed": False,
                    "check": "safety",
                    "message": "Potential hardcoded secrets detected"
                }
            
            dangerous_patterns = [
                (r'eval\s*\(', "Dangerous eval() call"),
                (r'exec\s*\(', "Dangerous exec() call"),
                (r'__import__\s*\(', "Dynamic import detected"),
            ]
            
            for pattern, message in dangerous_patterns:
                if re.search(pattern, code):
                    return {
                        "passed": False,
                        "check": "safety",
                        "message": message
                    }
            
            return {
                "passed": True,
                "check": "safety",
                "message": "Safety checks passed"
            }
            
        except OSError as e:
            return {
                "passed": False,
                "check": "safety",
                "message": f"Safety check failed: {e}",
                "error": str(e)
            }
    
    def _contains_hardcoded_secrets(self, code: str) -> bool:
        """Check for hardcoded API keys, passwords, etc."""
        secret_patterns = [
            r'api[_-]?key\s*=\s*["\'][a-zA-Z0-9_\-]{20,}["\']',
            r'secret[_-]?key\s*=\s*["\'][a-zA-Z0-9_\-]{20,}["\']',
            r'password\s*=\s*["\'][^"\'\s]{8,}["\']',
            r'Bearer\s+[a-zA-Z0-9_\-\.]+',
        ]
        
        for pattern in secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        
        return False
    
    def attempt_self_repair(self, refactor_result: RefactorResult,
                            validation_result: ValidationResult,
                            original_file: Path) -> RefactorResult:
        """Attempt to fix validation failures by re-prompting the AI."""
        if validation_result.passed:
            return refactor_result
        
        error_report = self._build_error_report(validation_result)
        
        try:
            with open(original_file, 'r') as f:
                original_code = f.read()
        except OSError as e:
            self.logger.error(f"Failed to read original file: {e}")
            return refactor_result
        
        repair_prompt = f"""{self.config.ai.system_prompt}

Your previous refactoring had validation errors. Please fix them.

## Original Code:
{original_code}

## Previous Attempt:
{refactor_result.refactored_code}

## Validation Errors:
{error_report}

Please provide corrected refactored code that addresses these errors.
Ensure the code is syntactically valid and passes all safety checks.

## Corrected Code:
"""
        
        from janitor.utils.ai_client import AIClient
        
        try:
            client = AIClient(self.config)
            corrected_code = client.complete(
                prompt=repair_prompt,
                max_tokens=self.config.ai.max_tokens,
                temperature=0.1
            )
        except Exception as e:
            self.logger.error(f"Self-repair failed: {e}")
            return refactor_result
        
        code_match = re.search(r'```python\n([\s\S]*?)\n```', corrected_code)
        if code_match:
            corrected_code = code_match.group(1)
        
        return RefactorResult(
            success=True,
            changes_made=refactor_result.changes_made,
            original_code=refactor_result.original_code,
            refactored_code=corrected_code,
            explanation="Self-repair attempt",
            issues_addressed=refactor_result.issues_addressed
        )
    
    def _build_error_report(self, validation_result: ValidationResult) -> str:
        """Build a detailed error report for the AI."""
        lines = ["Validation failed with the following issues:"]
        
        for check in validation_result.checks:
            if not check.get('passed', True):
                lines.append(f"- {check.get('message', 'Unknown error')}")
                if 'issues' in check:
                    for issue in check['issues']:
                        lines.append(f"  * {issue}")
        
        return '\n'.join(lines)

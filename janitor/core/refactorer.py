"""
Phase 3: AI-powered code refactoring.
"""

import re
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from janitor.config import Config
from janitor.core.linter import LintResult
from janitor.core.analyzer import AnalysisResult
from janitor.utils.ai_client import AIClient, AIProvider


@dataclass
class RefactorResult:
    """Result from AI refactoring operation."""
    success: bool
    changes_made: int
    original_code: str
    refactored_code: str
    explanation: str = ""
    issues_addressed: List[Dict] = field(default_factory=list)
    error: Optional[str] = None


class Refactorer:
    """AI-powered code refactoring interface."""
    
    def __init__(self, config: Config):
        """Initialize refactorer with configuration."""
        self.config = config
        self.ai_config = config.ai
        self.logger = logging.getLogger(__name__)
        self.ai_client = AIClient(config)
    
    def refactor(self, target: Path, analysis: AnalysisResult,
                 lint: LintResult) -> RefactorResult:
        """Perform AI-powered refactoring on target."""
        if target.is_file():
            return self._refactor_file(target, analysis, lint)
        if target.is_dir():
            return self._refactor_directory(target, analysis, lint)
        return RefactorResult(
            success=False,
            changes_made=0,
            original_code="",
            refactored_code="",
            error=f"Invalid target: {target}"
        )
    
    def _refactor_file(self, file_path: Path, analysis: AnalysisResult,
                       lint: LintResult) -> RefactorResult:
        """Refactor a single file using AI."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_code = f.read()
        except OSError as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            return RefactorResult(
                success=False,
                changes_made=0,
                original_code="",
                refactored_code="",
                error=f"Read error: {e}"
            )
        
        if not analysis.has_issues and not lint.has_issues:
            return RefactorResult(
                success=True,
                changes_made=0,
                original_code=original_code,
                refactored_code=original_code,
                explanation="No issues detected - no refactoring needed"
            )
        
        prompt = self._build_refactor_prompt(original_code, analysis, lint)
        
        try:
            refactored_code = self._call_ai_with_retry(prompt)
        except Exception as e:
            self.logger.error(f"AI refactoring failed: {e}")
            return RefactorResult(
                success=False,
                changes_made=0,
                original_code=original_code,
                refactored_code="",
                error=str(e)
            )
        
        refactored_code = self._extract_code(refactored_code)
        changes_made = self._estimate_changes(original_code, refactored_code)
        
        return RefactorResult(
            success=True,
            changes_made=changes_made,
            original_code=original_code,
            refactored_code=refactored_code,
            explanation="Refactoring completed successfully",
            issues_addressed=analysis.code_smells + analysis.security_issues
        )
    
    def _build_refactor_prompt(self, code: str, analysis: AnalysisResult,
                               lint: LintResult) -> str:
        """Build the AI prompt for refactoring."""
        issues_text = ""
        
        if analysis.code_smells:
            issues_text += "### Code Smells Detected:\n"
            for issue in analysis.code_smells:
                issues_text += f"- Line {issue['line']}: {issue['message']}\n"
                if 'suggestion' in issue:
                    issues_text += f"  Suggestion: {issue['suggestion']}\n"
        
        if analysis.security_issues:
            issues_text += "\n### CRITICAL SECURITY ISSUES DETECTED:\n"
            for issue in analysis.security_issues:
                severity = issue.get('severity', 'warning')
                issues_text += f"- Line {issue['line']}: {issue['message']} (Severity: {severity})\n"
                if 'suggestion' in issue:
                    issues_text += f"  Suggestion: {issue['suggestion']}\n"
        
        if analysis.radon_complexity:
            issues_text += "\n### Complexity Metrics:\n"
            max_complexity = 0
            if isinstance(analysis.radon_complexity, dict):
                for func_name, details in analysis.radon_complexity.items():
                    if isinstance(details, dict):
                        score = details.get('complexity', 0)
                        loc = details.get('loc', 0)
                        if score > max_complexity:
                            max_complexity = score
                        if score > 10:
                            issues_text += f"- High Complexity: '{func_name}' has score {score}\n"
                        if loc > 30:
                            issues_text += f"- Long Function: '{func_name}' is {loc} lines\n"
        
        if lint.has_issues:
            issues_text += "\n### Linting Issues:\n"
            for issue in lint.issues[:10]:
                issues_text += f"- Line {issue.get('line', '?')}: {issue.get('message', 'Unknown issue')}\n"
        
        prompt = f"""{self.ai_config.system_prompt}

## Static Analysis Report:
{issues_text if issues_text else "No issues detected - perform general code quality improvements."}

## Original Code:
```{self._get_code_language(code)}
{code}
```

## Task
Refactor the code above to address all identified issues while preserving all functionality. Return the complete, runnable code.

## Refactored Code:
"""
        return prompt
    
    def _get_code_language(self, code: str) -> str:
        """Detect language from code content."""
        if 'def ' in code or 'class ' in code or 'import ' in code:
            return 'python'
        if 'function' in code or 'const ' in code or 'let ' in code:
            return 'javascript'
        if 'interface ' in code or 'type ' in code:
            return 'typescript'
        return 'text'
    
    def _call_ai_with_retry(self, prompt: str) -> str:
        """Call AI API with retry logic."""
        max_retries = self.ai_config.max_retries
        retry_delay = 2
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = self.ai_client.complete(
                    prompt=prompt,
                    max_tokens=self.ai_config.max_tokens,
                    temperature=self.ai_config.temperature
                )
                return response
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"AI call failed (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                    retry_delay *= 2
        
        raise Exception(f"AI call failed after {max_retries} attempts: {last_error}")
    
    def _extract_code(self, response: str) -> str:
        """Extract code from AI response, removing markdown formatting."""
        code_block_pattern = r'```(\w*)\n([\s\S]*?)\n```'
        matches = re.findall(code_block_pattern, response)
        
        if matches:
            language, code = matches[-1]
            return code
        
        return response.strip()
    
    def _estimate_changes(self, original: str, refactored: str) -> int:
        """Estimate number of changes made."""
        orig_lines = set(original.splitlines())
        ref_lines = set(refactored.splitlines())
        
        changed = len(orig_lines.symmetric_difference(ref_lines))
        return changed
    
    def _refactor_directory(self, dir_path: Path, analysis: AnalysisResult,
                            lint: LintResult) -> RefactorResult:
        """Refactor all files in directory."""
        results = []
        
        for code_file in self._collect_code_files(dir_path):
            file_analysis = self._extract_file_analysis(code_file, analysis)
            file_lint = self._extract_file_lint(code_file, lint)
            
            result = self._refactor_file(code_file, file_analysis, file_lint)
            results.append(result)
        
        total_changes = sum(r.changes_made for r in results)
        successful_refactors = [r for r in results if r.success]
        combined_code = "\n\n".join(r.refactored_code for r in successful_refactors)
        
        return RefactorResult(
            success=any(r.success for r in results),
            changes_made=total_changes,
            original_code="",
            refactored_code=combined_code,
            explanation=f"Refactored {len(successful_refactors)} files"
        )
    
    def _collect_code_files(self, dir_path: Path) -> List[Path]:
        """Collect code files for processing."""
        code_files = []
        for ext in ['*.py', '*.js', '*.ts']:
            code_files.extend(dir_path.rglob(ext))
        return code_files
    
    def _extract_file_analysis(self, file_path: Path, 
                               analysis: AnalysisResult) -> AnalysisResult:
        """Extract analysis results for a specific file."""
        file_code_smells = [
            i for i in analysis.code_smells 
            if str(file_path) in str(i.get('file', ''))
        ]
        file_security = [
            i for i in analysis.security_issues 
            if str(file_path) in str(i.get('file', ''))
        ]
        
        return AnalysisResult(
            has_issues=len(file_code_smells) > 0 or len(file_security) > 0,
            issue_count=len(file_code_smells) + len(file_security),
            code_smells=file_code_smells,
            security_issues=file_security
        )
    
    def _extract_file_lint(self, file_path: Path, 
                           lint: LintResult) -> LintResult:
        """Extract lint results for a specific file."""
        file_issues = [
            i for i in lint.issues 
            if str(file_path) in str(i.get('file', ''))
        ]
        
        return LintResult(
            success=len(file_issues) == 0,
            has_issues=len(file_issues) > 0,
            issues=file_issues,
            auto_fixed=[]
        )

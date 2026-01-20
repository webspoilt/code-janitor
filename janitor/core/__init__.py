"""
Core module for Code Janitor.

This module contains the main processing phases:
- Linting: Basic code quality and formatting checks
- Static Analysis: Deep code analysis for issues and smells
- Refactoring: AI-powered code transformation
- Validation: Self-healing validation loop
- Backup: Rollback functionality
"""

from janitor.core.linter import Linter, LintResult
from janitor.core.analyzer import Analyzer, AnalysisResult
from janitor.core.refactorer import Refactorer, RefactorResult
from janitor.core.validator import Validator, ValidationResult
from janitor.core.backup import BackupManager

__all__ = [
    "Linter",
    "LintResult",
    "Analyzer",
    "AnalysisResult",
    "Refactorer",
    "RefactorResult",
    "Validator",
    "ValidationResult",
    "BackupManager",
]

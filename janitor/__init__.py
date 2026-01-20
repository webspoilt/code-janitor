"""
Code Janitor - Automated Code Refactoring Tool

A CLI tool that combines static analysis with LLM capabilities to
automatically detect, analyze, and clean up problematic code.
"""

__version__ = "1.0.0"
__author__ = "Code Janitor Team"

from janitor.cli import main

__all__ = ["main", "__version__"]

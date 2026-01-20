"""
Configuration management for Code Janitor.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import yaml


@dataclass
class LinterConfig:
    """Configuration for the linting phase."""
    enabled: bool = True
    auto_fix: bool = True
    max_line_length: int = 120
    target_python_version: str = "3.10"
    rules: Dict[str, bool] = field(default_factory=lambda: {
        "E": True,
        "W": True,
        "F": True,
        "I": True,
        "N": True,
    })


@dataclass
class AnalyzerConfig:
    """Configuration for static analysis."""
    enabled: bool = True
    max_nesting_depth: int = 4
    max_function_lines: int = 50
    max_cyclomatic_complexity: int = 10
    security_checks: bool = True
    complexity_checks: bool = True
    dead_code_detection: bool = True


@dataclass
class AIConfig:
    """Configuration for AI integration."""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    max_retries: int = 3
    timeout_seconds: int = 60
    max_tokens: int = 4000
    temperature: float = 0.2
    system_prompt: str = field(default_factory=lambda: """\
You are an expert Senior Developer and code quality specialist. Your task is to refactor the provided code.
Goals:
1. Fix all identified security vulnerabilities (SQL injection, hardcoded secrets, dangerous functions, etc.).
2. Resolve code smells (deep nesting, long functions, high complexity, dead code).
3. Improve performance (replace inefficient algorithms, optimize data structures).
4. Ensure strict type hints and comprehensive error handling.
5. Follow PEP 8 style guidelines and best practices.

Constraints:
- Return ONLY the valid code block. No explanations outside the code.
- Preserve the exact imports from the original code.
- Do not change the logic intentionally, only clean and optimize it.
- Wrap the final code in ```python ``` code blocks.
- If you're unsure about the intent of code, keep it unchanged rather than guessing.
- Prioritize correctness and safety over cleverness.
- Add inline comments explaining significant changes.
""")


@dataclass
class ValidatorConfig:
    """Configuration for the validation loop."""
    run_linter_after: bool = True
    run_static_analysis: bool = True
    run_tests: bool = True
    max_validation_retries: int = 2
    fail_on_security_issues: bool = True


@dataclass
class BackupConfig:
    """Configuration for backup and rollback."""
    enabled: bool = True
    backup_dir: Path = Path(".janitor_backups")
    max_backups: int = 5


@dataclass
class Config:
    """Main configuration container."""
    linter: LinterConfig = field(default_factory=LinterConfig)
    analyzer: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    validator: ValidatorConfig = field(default_factory=ValidatorConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    
    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'Config':
        """Load configuration from file or use defaults."""
        config = cls()
        
        if config_path is None:
            search_paths = [
                Path("janitor.yaml"),
                Path("janitor.yml"),
                Path(".janitor.yaml"),
                Path(".janitor.yml"),
                Path("~/.config/code-janitor/config.yaml").expanduser(),
            ]
            
            for path in search_paths:
                if path.exists():
                    config_path = path
                    break
        
        if config_path and config_path.exists():
            cls._apply_file_config(config, config_path)
        
        cls._apply_env_overrides(config)
        
        return config
    
    @classmethod
    def _apply_file_config(cls, config: 'Config', path: Path) -> None:
        """Apply configuration from YAML file."""
        try:
            with open(path, 'r') as f:
                file_config = yaml.safe_load(f) or {}
        except OSError as e:
            return
        
        if 'linter' in file_config:
            linter_data = file_config['linter']
            if isinstance(linter_data, dict):
                config.linter.enabled = linter_data.get('enabled', config.linter.enabled)
                config.linter.auto_fix = linter_data.get('auto_fix', config.linter.auto_fix)
                config.linter.max_line_length = linter_data.get(
                    'max_line_length', config.linter.max_line_length
                )
        
        if 'analyzer' in file_config:
            analyzer_data = file_config['analyzer']
            if isinstance(analyzer_data, dict):
                config.analyzer.max_nesting_depth = analyzer_data.get(
                    'max_nesting_depth', config.analyzer.max_nesting_depth
                )
                config.analyzer.max_function_lines = analyzer_data.get(
                    'max_function_lines', config.analyzer.max_function_lines
                )
        
        if 'ai' in file_config:
            ai_data = file_config['ai']
            if isinstance(ai_data, dict):
                config.ai.provider = ai_data.get('provider', config.ai.provider)
                config.ai.model = ai_data.get('model', config.ai.model)
                config.ai.temperature = ai_data.get('temperature', config.ai.temperature)
    
    @classmethod
    def _apply_env_overrides(cls, config: 'Config') -> None:
        """Apply environment variable overrides."""
        provider = os.getenv('JANITOR_AI_PROVIDER')
        if provider:
            config.ai.provider = provider
        
        model = os.getenv('JANITOR_AI_MODEL')
        if model:
            config.ai.model = model
        
        api_key = os.getenv('JANITOR_API_KEY')
        if api_key:
            config.ai.api_key = api_key
        
        nesting_val = os.getenv('JANITOR_MAX_NESTING')
        if nesting_val:
            try:
                config.analyzer.max_nesting_depth = int(nesting_val)
            except ValueError:
                pass

#!/usr/bin/env python3
"""
Code Janitor - Automated Code Refactoring Tool

A CLI tool that combines static analysis with LLM capabilities to
automatically detect, analyze, and clean up problematic code.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import Optional

from janitor.config import Config
from janitor.core.linter import Linter
from janitor.core.analyzer import Analyzer
from janitor.core.refactorer import Refactorer
from janitor.core.validator import Validator
from janitor.core.backup import BackupManager
from janitor.utils.report import ReportGenerator
from janitor.utils.formatting import RichConsole

logging.basicConfig(
    level=logging.WARNING, # Reduced noise in default logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CodeJanitorCLI:
    """Main CLI interface for the Code Janitor tool."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the CLI with optional configuration path."""
        self.config = Config.load(config_path)
        self.backup_manager = BackupManager(self.config.backup.backup_dir)
        self.report_generator = ReportGenerator()
        self.console = RichConsole()
    
    def run_check(self, target: Path, output_format: str = 'text') -> int:
        """
        Run analysis without making changes.
        """
        self.console.log_info(f"Starting check on: {target}")
        
        issue_count = 0
        
        self.console.print("[bold cyan]Phase 1: Linting...[/bold cyan]")
        linter = Linter(self.config)
        lint_results = linter.analyze(target)
        
        if lint_results.has_issues:
            issue_count += len(lint_results.issues)
            self.report_generator.add_lint_results(lint_results)
        
        self.console.print("[bold cyan]Phase 2: Static Analysis...[/bold cyan]")
        analyzer = Analyzer(self.config)
        analysis_results = analyzer.analyze(target)
        
        if analysis_results.has_issues:
            issue_count += analysis_results.issue_count
            self.report_generator.add_analysis_results(analysis_results)
        
        report = self.report_generator.generate(output_format)
        self._display_report(report, output_format)
        
        if issue_count > 0:
            self.console.log_warning(f"Found {issue_count} issues.")
            return 1
        else:
            self.console.log_success("No issues found.")
            return 0
    
    def run_clean(self, target: Path, show_diff: bool = False, 
                  dry_run: bool = False) -> int:
        """
        Run full cleaning process with AI refactoring.
        """
        self.console.log_info(f"Starting clean operation on: {target}")
        
        if not dry_run:
            self.backup_manager.create_backup(target)
        
        results = []
        
        # Phase 1
        self.console.print("[bold cyan]Phase 1: Linting and formatting...[/bold cyan]")
        linter = Linter(self.config)
        lint_results = linter.analyze(target, auto_fix=not dry_run)
        
        if lint_results.auto_fixed:
            self.console.log_success(f"Auto-fixed {len(lint_results.auto_fixed)} linting issues")
            results.append(('Linting', len(lint_results.auto_fixed), 'auto-fixed'))
        
        # Phase 2
        self.console.print("[bold cyan]Phase 2: Static analysis...[/bold cyan]")
        analyzer = Analyzer(self.config)
        analysis_results = analyzer.analyze(target)
        
        refactor_results = None
        
        if analysis_results.has_issues:
            self.console.log_warning(f"Found {analysis_results.issue_count} issues requiring attention")
            results.append(('Analysis', analysis_results.issue_count, 'identified'))
        
        # Phase 3
        if (analysis_results.has_issues or lint_results.has_issues) and not dry_run:
            self.console.print("[bold cyan]Phase 3: AI refactoring...[/bold cyan]")
            refactorer = Refactorer(self.config)
            validator = Validator(self.config)
            
            refactor_results = refactorer.refactor(
                target, 
                analysis_results,
                lint_results
            )
            
            if not refactor_results.success:
                self.console.log_error(f"Refactoring failed: {refactor_results.error}")
                return 1
            
            self.console.print("Validating refactored code...")
            validation_passed = validator.validate(refactor_results)
            
            if validation_passed:
                self.console.log_success("Validation passed - applying changes")
                validator.apply_changes(refactor_results)
                results.append(('Refactoring', refactor_results.changes_made, 'applied'))
            else:
                self.console.log_error("Validation failed - rolling back")
                self.backup_manager.rollback(target)
                return 1
        elif dry_run and (analysis_results.has_issues or lint_results.has_issues):
            self.console.print("[bold yellow]Dry Run: Skipping AI Refactoring application.[/bold yellow]")
            # We can still run it to generate the preview if we wanted, but sticking to logic
            # If the user wants to see the diff of what WOULD happen, we should probably run the AI but not apply.
            # Let's run it for the diff.
            self.console.print("[bold cyan]Phase 3: AI Refactoring (Preview)...[/bold cyan]")
            refactorer = Refactorer(self.config)
            refactor_results = refactorer.refactor(target, analysis_results, lint_results)
            if refactor_results.success:
                self.console.log_success("AI suggested refactoring available.")
            else:
                 self.console.log_error(f"AI Refactoring failed: {refactor_results.error}")

        
        report = self.report_generator.generate('text', results)
        print("\n" + report)
        
        if show_diff:
            self._show_diff(target, dry_run=dry_run, refactor_results=refactor_results)
        
        return 0
    
    def run_web(self, host: str = "0.0.0.0", port: int = 8000) -> int:
        """
        Run the Web UI server.
        """
        try:
            import uvicorn
        except ImportError:
            self.console.log_error("Web dependencies not installed. Run: pip install fastapi uvicorn")
            return 1
            
        self.console.log_info(f"Starting Code Janitor Web UI on http://{host}:{port}")
        self.console.log_info("Press Ctrl+C to stop.")
        
        try:
            uvicorn.run("janitor.web.app:app", host=host, port=port, reload=False)
            return 0
        except Exception as e:
            self.console.log_error(f"Failed to start web server: {e}")
            return 1

    def run_init(self, force: bool = False) -> int:
        """
        Initialize configuration file.
        """
        config_path = Path("janitor.yaml")
        if config_path.exists() and not force:
            self.console.log_error("janitor.yaml already exists. Use --force to overwrite.")
            return 1
            
        self.console.log_info("Initializing configuration...")
        
        # Detect Ollama
        use_ollama = False
        try:
            import requests
            try:
                self.console.print("Checking for Ollama instance...")
                resp = requests.get("http://localhost:11434/api/tags", timeout=2)
                if resp.status_code == 200:
                    self.console.log_success("Ollama detected locally!")
                    use_ollama = True
            except requests.RequestException:
                pass
        except ImportError:
            pass
            
        config_content = """# Code Janitor Configuration

linter:
  enabled: true
  auto_fix: true
  max_line_length: 120

analyzer:
  max_nesting_depth: 4
  max_function_lines: 50
  max_cyclomatic_complexity: 10
  security_checks: true

ai:
"""
        if use_ollama:
            config_content += """  provider: ollama
  model: llama3  # Change to your preferred model
  temperature: 0.2
"""
            self.console.print("[bold green]Configuring for local Ollama usage.[/bold green]")
        else:
            config_content += """  provider: openai
  model: gpt-4
  temperature: 0.2
  # api_key: "your-key-here"  # Or set OPENAI_API_KEY env var
"""
            self.console.print("[yellow]Configuring for OpenAI (requires API key).[/yellow]")

        config_content += """
backup:
  enabled: true
  backup_dir: .janitor_backups
  max_backups: 5
"""
        
        try:
            with open(config_path, 'w') as f:
                f.write(config_content)
            self.console.log_success(f"Configuration written to {config_path.absolute()}")
            return 0
        except OSError as e:
            self.console.log_error(f"Failed to write configuration: {e}")
            return 1

    def _display_report(self, report: str, fmt: str) -> None:
        """Display the generated report."""
        if fmt == 'json':
            print(report)
        elif fmt == 'html':
            with open("report.html", "w") as f:
                f.write(report)
            self.console.log_success("HTML report saved to: report.html")
        else:
            self.console.print_panel(report, title=f"Analysis Report", style="green")
    
    def _show_diff(self, target: Path, dry_run: bool = False, refactor_results=None) -> None:
        """Show diff of changes made."""
        original_content = ""
        modified_content = ""
        
        try:
            if dry_run:
                # In dry run, current file is original
                with open(target, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                if refactor_results and refactor_results.success:
                    modified_content = refactor_results.refactored_code
                else:
                    self.console.log_info("No refactoring changes to diff.")
                    return
            else:
                # In real run, current file is modified. Find backup for original.
                backup = self.backup_manager._find_latest_backup(target)
                if backup:
                    # Backup usually is a folder with metadata or the file itself?
                    # BackupManager: create_backup returns path.
                    # If target is file, backup is file.
                    with open(backup, 'r', encoding='utf-8') as f:
                        original_content = f.read()
                    with open(target, 'r', encoding='utf-8') as f:
                        modified_content = f.read()
                else:
                     self.console.log_warning("Could not find backup for diff comparison.")
                     return

            self.console.print_diff(original_content, modified_content, filename=target.name)
            
        except Exception as e:
            self.console.log_error(f"Failed to generate diff: {e}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description='Code Janitor - Automated Code Refactoring Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  janitor init                          # Create configuration
  janitor web                           # Start Web UI
  janitor check src/app.py              # Analyze without modifying
  janitor clean src/app.py              # Clean and refactor
  janitor clean src/ --diff             # Show changes as diff
  janitor clean src/ --dry-run          # Preview without applying
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize configuration')
    init_parser.add_argument('--force', action='store_true', help='Overwrite existing config')
    
    # Web command
    web_parser = subparsers.add_parser('web', help='Start Web UI')
    web_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    web_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')

    check_parser = subparsers.add_parser('check', help='Analyze code without changes')
    check_parser.add_argument('target', type=Path, help='File or directory to analyze')
    check_parser.add_argument('--format', choices=['text', 'json', 'html'], 
                              default='text', help='Output format')
    
    clean_parser = subparsers.add_parser('clean', help='Clean and refactor code')
    clean_parser.add_argument('target', type=Path, help='File or directory to clean')
    clean_parser.add_argument('--diff', action='store_true', help='Show diff of changes')
    clean_parser.add_argument('--dry-run', action='store_true', 
                              help='Preview changes without applying')
    
    parser.add_argument('--config', type=Path, help='Path to configuration file')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increase verbosity (use -vv for debug)')
    
    args = parser.parse_args()
    
    if args.verbose >= 2:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    try:
        cli = CodeJanitorCLI(config_path=args.config)
        
        if args.command == 'check':
            exit_code = cli.run_check(args.target, args.format)
        elif args.command == 'clean':
            # run_clean takes dry_run, not dry_run (name collision in args)
            exit_code = cli.run_clean(args.target, args.diff, args.dry_run)
        elif args.command == 'init':
            exit_code = cli.run_init(args.force)
        elif args.command == 'web':
            exit_code = cli.run_web(args.host, args.port)
        else:
            exit_code = 1
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except OSError as e:
        print(f"IO error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        if args.verbose >= 2:
            raise
        sys.exit(1)


if __name__ == '__main__':
    main()

# Code Janitor

Automated Code Refactoring Tool with AI capabilities.

## Overview

Code Janitor is an intelligent CLI tool that combines static analysis with LLM capabilities to automatically detect, analyze, and clean up problematic code. It identifies code smells, security vulnerabilities, and performance issues, then leverages AI to refactor and optimize the codebase while maintaining functional correctness.

## Features

- **Multi-phase Analysis**: Parsing, linting, static analysis, and AI transformation
- **Code Smell Detection**: Identifies deep nesting, long functions, dead code, and duplicates
- **Security Scanning**: Detects potential vulnerabilities like SQL injection, hardcoded secrets
- **AI Refactoring**: Uses large language models for intelligent code improvements
- **Validation Loop**: Self-healing validation ensures refactored code is correct
- **Backup & Rollback**: Automatic backups with easy rollback capability
- **Multi-language Support**: Starting with Python (JavaScript/TypeScript planned)

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd code-janitor

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Configuration

Create a `janitor.yaml` configuration file:

```yaml
linter:
  enabled: true
  auto_fix: true
  max_line_length: 120

analyzer:
  max_nesting_depth: 4
  max_function_lines: 50
  max_cyclomatic_complexity: 10

ai:
  provider: openai  # openai, anthropic, ollama
  model: gpt-4
  temperature: 0.2
```

Set your API key:

```bash
export OPENAI_API_KEY="your-api-key"
# or
export ANTHROPIC_API_KEY="your-api-key"
```

## Usage

### Check Code (Analysis Only)

```bash
# Analyze a single file
janitor check src/app.py

# Analyze a directory
janitor check src/

# Output as JSON
janitor check src/ --format json
```

### Clean and Refactor

```bash
# Clean and refactor a file
janitor clean src/app.py

# Show diff of changes
janitor clean src/app.py --diff

# Preview without applying changes
janitor clean src/app.py --dry-run

# Clean entire directory
janitor clean src/
```

## Architecture

### Phase 1: Parsing and Linting

The first phase reads and validates input code at the most basic level. It parses the code into an Abstract Syntax Tree (AST) and applies linting rules to catch syntax errors, style violations, and obvious anti-patterns.

**Tools**: Ruff, Black, or generic AST-based analysis

### Phase 2: Static Analysis

The second phase performs deeper analysis to identify potential security vulnerabilities, complex logic, and performance issues. Static analysis tools examine the code without executing it.

**Tools**: AST-based analysis, security pattern matching

### Phase 3: AI Transformation

The third phase leverages large language models to intelligently refactor code based on issues identified in previous phases. The AI receives a carefully crafted prompt with the original code, analysis report, and specific instructions.

**Providers**: OpenAI (GPT-4), Anthropic (Claude), Ollama (local models)

### Validation Loop

After AI refactoring, the tool validates the output through:
1. Syntax checking
2. Linting
3. Static analysis
4. Safety rule verification

If validation fails, the AI attempts self-repair. After maximum retries, it rolls back to the original code.

## Supported Code Smells

- **Deep Nesting**: Functions with excessive nested conditionals/loops
- **Long Functions**: Functions exceeding line thresholds
- **Dead Code**: Unused variables, functions, or unreachable code
- **High Complexity**: Functions with high cyclomatic complexity
- **Security Issues**: SQL injection, hardcoded secrets, dangerous functions

## API Integration

### OpenAI

```yaml
ai:
  provider: openai
  model: gpt-4
  temperature: 0.2
```

### Anthropic

```yaml
ai:
  provider: anthropic
  model: claude-sonnet-4-20250514
  temperature: 0.2
```

### Ollama (Local)

```yaml
ai:
  provider: ollama
  model: llama3
```

## Development

```bash
# Run tests
pytest

# Type checking
mypy janitor/

# Format code
black janitor/

# Lint
ruff check janitor/
```

## License

MIT License - see LICENSE file for details.

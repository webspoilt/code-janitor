<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:3776AB,50:FFD43B,100:3776AB&height=200&section=header&text=Code%20Janitor&fontSize=70&fontColor=fff&animation=fadeIn&fontAlignY=35&desc=AI-Powered%20Code%20Refactoring%20Tool&descAlignY=55&descSize=16"/>

[![Python](https://img.shields.io/badge/Python-89.3%25-3776AB?style=for-the-badge&logo=python&logoColor=white)]()
[![HTML](https://img.shields.io/badge/HTML-10.7%25-E34F26?style=for-the-badge&logo=html5&logoColor=white)]()
[![AI](https://img.shields.io/badge/AI-Enabled-FF006E?style=for-the-badge)]()
[![Live Demo](https://img.shields.io/badge/Live_Demo-00C853?style=for-the-badge)](https://code-janitor-sigma.vercel.app)

**Clean Code. Automatically.**

</div>

---

## 🎯 Overview

Code Janitor is an intelligent CLI tool that combines **static analysis** with **LLM capabilities** to automatically detect, analyze, and clean up problematic code. It identifies code smells, security vulnerabilities, and performance issues, then leverages AI to refactor and optimize the codebase while maintaining functional correctness.

---

## ✨ Features

### 🔍 Multi-phase Analysis
| Phase | Description |
|-------|-------------|
| **Parsing** | AST-based code understanding |
| **Linting** | Style and best practice checks |
| **Static Analysis** | Deep code quality assessment |
| **AI Transformation** | Intelligent refactoring suggestions |

### 🛡️ Code Smell Detection
- Deep nesting detection
- Long function identification
- Dead code elimination
- Duplicate code detection
- Complexity analysis

### 🔒 Security Scanning
- SQL injection vulnerabilities
- Hardcoded secrets detection
- XSS vulnerability identification
- Insecure dependency checks

### 🤖 AI Refactoring
- Uses Large Language Models for intelligent improvements
- Maintains functional correctness
- Generates human-readable code
- Explains changes made

---

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/webspoilt/code-janitor.git
cd code-janitor

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Add your OpenAI API key to .env

# Run on a file
python app.py clean path/to/your/file.py

# Run on a directory
python app.py clean path/to/project/ --recursive
```

---

## 📊 Configuration

Create `janitor.yaml` in your project root:

```yaml
# Code Janitor Configuration
analysis:
  max_function_length: 50
  max_nesting_depth: 4
  max_cyclomatic_complexity: 10

security:
  check_secrets: true
  check_sql_injection: true
  check_xss: true

ai:
  model: gpt-4
  temperature: 0.3
  max_tokens: 2000

ignore:
  - "**/tests/**"
  - "**/venv/**"
  - "**/__pycache__/**"
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Code Input                            │
└─────────────────────────┬───────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
│   Parser     │  │   Linter    │  │    AST      │
│              │  │             │  │   Analyzer  │
└───────┬──────┘  └──────┬──────┘  └──────┬──────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
              ┌──────────▼──────────┐
              │   Issue Detection   │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   AI Refactoring    │
              │   (LLM Pipeline)    │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   Validation Loop   │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │   Clean Code Output │
              └─────────────────────┘
```

---

## 🌐 Live Demo

Try Code Janitor online: **[code-janitor-sigma.vercel.app](https://code-janitor-sigma.vercel.app)**

---

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

<div align="center">

**Built with 🤖 by [webspoilt](https://github.com/webspoilt)**

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:3776AB,50:FFD43B,100:3776AB&height=100&section=footer"/>

</div>

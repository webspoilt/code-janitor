"""
File operations utilities.
"""

from pathlib import Path
from typing import List, Optional


def read_file(file_path: Path) -> str:
    """Read file contents."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_file(file_path: Path, content: str) -> None:
    """Write content to file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def find_code_files(directory: Path, extensions: Optional[List[str]] = None) -> List[Path]:
    """Find all code files in directory."""
    if extensions is None:
        extensions = ['.py', '.js', '.ts', '.jsx', '.tsx']
    
    code_files = []
    for ext in extensions:
        code_files.extend(directory.rglob(f'*{ext}'))
    
    return code_files


def get_file_extension(file_path: Path) -> str:
    """Get file extension in lowercase."""
    return file_path.suffix.lower()


def is_code_file(file_path: Path) -> bool:
    """Check if file is a code file."""
    code_extensions = {'.py', '.pyw', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h'}
    return get_file_extension(file_path) in code_extensions

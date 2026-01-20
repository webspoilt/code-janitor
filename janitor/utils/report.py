"""
Report generation utilities.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class Report:
    """Report container."""
    generated_at: str
    target: str
    phases: List[Dict[str, Any]]
    summary: Dict[str, int]
    details: Dict[str, Any]


class ReportGenerator:
    """Generates formatted reports for analysis results."""
    
    def __init__(self):
        """Initialize report generator."""
        self.sections = []
    
    def add_lint_results(self, result) -> None:
        """Add linting results to report."""
        self.sections.append({
            "phase": "Linting",
            "issues_found": len(result.issues),
            "auto_fixed": len(result.auto_fixed),
            "details": result.issues[:20]
        })
    
    def add_analysis_results(self, result) -> None:
        """Add analysis results to report."""
        self.sections.append({
            "phase": "Static Analysis",
            "issues_found": result.issue_count,
            "security_issues": len(result.security_issues),
            "code_smells": len(result.code_smells),
            "details": {
                "security_issues": result.security_issues[:20],
                "code_smells": result.code_smells[:20],
                "by_severity": {
                    sev: len(items) 
                    for sev, items in result.issues_by_severity.items()
                },
                "by_type": {
                    type_: len(items) 
                    for type_, items in result.issues_by_type.items()
                },
                "complexity_metrics": result.radon_complexity
            }
        })
    
    def generate(self, fmt: str = 'text', 
                 additional_results: Optional[List[tuple]] = None) -> str:
        """Generate report in specified format."""
        report = Report(
            generated_at=datetime.now().isoformat(),
            target="",
            phases=self.sections,
            summary=self._calculate_summary(),
            details={}
        )
        
        if fmt == 'json':
            return self._generate_json(report)
        if fmt == 'html':
            return self._generate_html(report)
        return self._generate_text(report, additional_results)
    
    def _calculate_summary(self) -> Dict[str, int]:
        """Calculate summary statistics."""
        total_issues = sum(s.get('issues_found', 0) for s in self.sections)
        auto_fixed = sum(s.get('auto_fixed', 0) for s in self.sections)
        
        return {
            "total_issues": total_issues,
            "auto_fixed": auto_fixed,
            "requires_attention": total_issues - auto_fixed
        }
    
    def _generate_text(self, report: Report,
                       additional_results: Optional[List[tuple]] = None) -> str:
        """Generate plain text report."""
        lines = []
        lines.append("=" * 60)
        lines.append("CODE JANITOR REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {report.generated_at}")
        lines.append("")
        
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"  Total Issues: {report.summary['total_issues']}")
        lines.append(f"  Auto-Fixed: {report.summary['auto_fixed']}")
        lines.append(f"  Requires Attention: {report.summary['requires_attention']}")
        lines.append("")
        
        lines.append("DETAILS BY PHASE")
        lines.append("-" * 40)
        
        for section in report.phases:
            lines.append(f"\n{section['phase']}:")
            lines.append(f"  Issues Found: {section.get('issues_found', 0)}")
            
            if section.get('auto_fixed', 0) > 0:
                lines.append(f"  Auto-Fixed: {section['auto_fixed']}")
            
            if 'security_issues' in section and section['security_issues']:
                lines.append(f"  Security Issues: {section['security_issues']}")
                details = section.get('details', {})
                if 'security_issues' in details:
                    for issue in details['security_issues'][:10]:
                        lines.append(f"    - Line {issue.get('line', '?')}: {issue.get('message', 'Unknown')}")
            
            if 'code_smells' in section and section['code_smells']:
                lines.append(f"  Code Smells: {section['code_smells']}")
                details = section.get('details', {})
                if 'code_smells' in details:
                    for issue in details['code_smells'][:10]:
                        lines.append(f"    - Line {issue.get('line', '?')}: {issue.get('message', 'Unknown')}")
            
            details = section.get('details', {})
            if 'complexity_metrics' in details and details['complexity_metrics']:
                lines.append("  Complexity Metrics:")
                for func_name, metrics in details['complexity_metrics'].items():
                    if isinstance(metrics, dict):
                        complexity = metrics.get('complexity', 0)
                        lines.append(f"    - {func_name}: complexity={complexity}")
        
        lines.append("")
        lines.append("=" * 60)
        
        return '\n'.join(lines)
    
    def _generate_json(self, report: Report) -> str:
        """Generate JSON report."""
        return json.dumps({
            "generated_at": report.generated_at,
            "summary": report.summary,
            "phases": report.phases
        }, indent=2)
    
    def _generate_html(self, report: Report) -> str:
        """Generate HTML report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Code Janitor Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .phase {{ margin: 20px 0; padding: 15px; border-left: 4px solid #007acc; }}
    </style>
</head>
<body>
    <h1>Code Janitor Report</h1>
    <p>Generated: {report.generated_at}</p>
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Issues: {report.summary['total_issues']}</p>
        <p>Auto-Fixed: {report.summary['auto_fixed']}</p>
    </div>
</body>
</html>
"""
        return html

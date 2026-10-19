import json
from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.table import Table

console = Console()

# 1. Define Strict Pydantic Output Schemas
class TicketRisk(BaseModel):
    ticket_id: str
    service: str
    verdict: Literal["PASS", "WARNING", "BLOCKER"]
    issue_detected: str = Field(description="Specific discrepancy found")
    remediation_step: str = Field(description="Action required by release coordinator")

class ReleaseAuditReport(BaseModel):
    overall_status: Literal["GO", "CONDITIONAL_GO", "NO_GO"]
    confidence_score: int = Field(description="0 to 100 percentage score")
    summary: str = Field(description="Executive summary of the release readiness")
    ticket_evaluations: List[TicketRisk]

# 2. Load Local Synthetic Data
with open("manifest.json", "r") as f:
    manifest_data = json.load(f)

# 3. Initialize Local Qwen 2.5 14B via Ollama
llm = ChatOllama(
    model="qwen2.5:14b",
    temperature=0.0
)

# Bind the Pydantic schema to force structured JSON output
structured_llm = llm.with_structured_output(ReleaseAuditReport)

console.print("[bold yellow]Auditing release manifest with local Qwen 2.5 (14B)...[/bold yellow]\n")

prompt = f"""
You are an expert Release Gatekeeper and Change Advisory Board (CAB) auditor.
Audit the following release manifest tickets against these governance rules:
1. BLOCKER (NO-GO): Any ticket with git_pr_status != 'Merged'.
2. BLOCKER (NO-GO): Any db_migration == True where rollback_plan_attached == False.
3. BLOCKER (NO-GO): Any ticket blocked_by another ticket that has a BLOCKER.
4. WARNING: Any ticket where uat_signoff == False.
5. PASS: All checks clean.

Release Manifest Data:
{json.dumps(manifest_data, indent=2)}
"""

# 4. Execute Inference Locally
report = structured_llm.invoke(prompt)

# 5. Render Pretty Terminal Dashboard
status_color = "green" if report.overall_status == "GO" else ("yellow" if report.overall_status == "CONDITIONAL_GO" else "red")
console.print(f"[bold]Verdict:[/bold] [{status_color}]{report.overall_status}[/{status_color}] | [bold]Confidence Score:[/bold] {report.confidence_score}%\n")
console.print(f"[italic]{report.summary}[/italic]\n")

table = Table(title="Ticket Audit Breakdown", header_style="bold cyan")
table.add_column("Ticket ID", style="bold")
table.add_column("Service")
table.add_column("Verdict")
table.add_column("Issue Detected")
table.add_column("Remediation Step")

for item in report.ticket_evaluations:
    verdict_style = "green" if item.verdict == "PASS" else ("yellow" if item.verdict == "WARNING" else "red bold")
    table.add_row(
        item.ticket_id,
        item.service,
        f"[{verdict_style}]{item.verdict}[/{verdict_style}]",
        item.issue_detected,
        item.remediation_step
    )

console.print(table)

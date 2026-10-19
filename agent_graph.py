import json
from typing import List, Dict, Any, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END

# --- Dynamic Schemas ---
class DynamicTicketAudit(BaseModel):
    ticket_id: str
    country: str
    module: str
    verdict: Literal["PASS", "WARNING", "BLOCKER"]
    issue_detected: str = Field(description="Specific discrepancy found against rules")
    remediation_step: str = Field(description="Action required by release coordinator")

class AgentState(TypedDict):
    manifest: List[Dict[str, Any]]
    governance_rules: List[str]
    audited_tickets: Dict[str, DynamicTicketAudit]
    final_verdict: str
    confidence_score: int
    cab_report: str

llm = ChatOllama(model="qwen2.5:14b", temperature=0.0)

# --- Node 1: Dynamic Governance Evaluator ---
def evaluate_dynamic_tickets_node(state: AgentState):
    audited = {}
    
    class SingleAudit(BaseModel):
        verdict: Literal["PASS", "WARNING", "BLOCKER"]
        issue_detected: str
        remediation_step: str

    structured_llm = llm.with_structured_output(SingleAudit)
    rules_text = "\n".join([f"- {r}" for r in state["governance_rules"]])
    
    for item in state["manifest"]:
        prompt = f"""
        You are an Enterprise Release Gatekeeper auditing a multi-country migration.
        Evaluate this work item against these program governance rules:
        {rules_text}

        Work Item Data (including dynamic custom parameters):
        {json.dumps(item, indent=2)}
        """
        result = structured_llm.invoke(prompt)
        audited[item["ticket_id"]] = DynamicTicketAudit(
            ticket_id=item["ticket_id"],
            country=item.get("country", "Global"),
            module=item.get("module", "General"),
            verdict=result.verdict,
            issue_detected=result.issue_detected,
            remediation_step=result.remediation_step
        )
    return {"audited_tickets": audited}

# --- Node 2: Dependency Resolver ---
def dependency_resolver_node(state: AgentState):
    tickets = state["audited_tickets"]
    for item in state["manifest"]:
        t_id = item["ticket_id"]
        for parent_id in item.get("blocked_by", []):
            if parent_id in tickets and tickets[parent_id].verdict == "BLOCKER":
                current = tickets[t_id]
                tickets[t_id] = DynamicTicketAudit(
                    ticket_id=current.ticket_id,
                    country=current.country,
                    module=current.module,
                    verdict="BLOCKER",
                    issue_detected=f"Cascading Blocker: Upstream item {parent_id} ({tickets[parent_id].module}) is blocked.",
                    remediation_step=f"Resolve blocker on {parent_id} before cutting over {t_id}."
                )
    return {"audited_tickets": tickets}

# --- Node 3: Executive CAB Synthesizer ---
def cab_synthesizer_node(state: AgentState):
    tickets = list(state["audited_tickets"].values())
    blockers = [t for t in tickets if t.verdict == "BLOCKER"]
    warnings = [t for t in tickets if t.verdict == "WARNING"]
    
    if blockers:
        verdict = "NO_GO"
        confidence = max(10, 100 - (len(blockers) * 25))
    elif warnings:
        verdict = "CONDITIONAL_GO"
        confidence = max(50, 100 - (len(warnings) * 10))
    else:
        verdict = "GO"
        confidence = 100
        
    summary = f"Multi-Country Cutover Audit: Evaluated {len(tickets)} tracks across {len(set(t.country for t in tickets))} market(s). {len(blockers)} Blocker(s), {len(warnings)} Warning(s)."
    return {"final_verdict": verdict, "confidence_score": confidence, "cab_report": summary}

# --- Compile Graph ---
builder = StateGraph(AgentState)
builder.add_node("evaluate", evaluate_dynamic_tickets_node)
builder.add_node("resolve", dependency_resolver_node)
builder.add_node("synthesize", cab_synthesizer_node)

builder.add_edge(START, "evaluate")
builder.add_edge("evaluate", "resolve")
builder.add_edge("resolve", "synthesize")
builder.add_edge("synthesize", END)

graph = builder.compile()

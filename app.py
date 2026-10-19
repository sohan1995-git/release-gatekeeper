import json
import streamlit as st
import pandas as pd
from agent_graph import graph
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

st.set_page_config(page_title="RelEase-AI | Multi-Country Gatekeeper", page_icon="🌍", layout="wide")

st.title("🌍 RelEase-AI: Multi-Country Release Gatekeeper")
st.markdown("Autonomous cutover governance for multi-market SuccessFactors & 3rd-Party legacy transformations.")

# --- Default Multi-Country Dataset ---
DEFAULT_MANIFEST = [
  {
    "ticket_id": "CR-SWE-01",
    "country": "Sweden",
    "module": "SuccessFactors Core HR",
    "legacy_system": "None (Greenfield)",
    "uat_signoff": True,
    "parallel_payroll_run": True,
    "cutover_blackout_hours": 12,
    "blocked_by": []
  },
  {
    "ticket_id": "CR-DEU-02",
    "country": "Germany",
    "module": "Payroll Integration (ADP)",
    "legacy_system": "ADP GlobalView",
    "uat_signoff": False,
    "parallel_payroll_run": False,
    "cutover_blackout_hours": 48,
    "blocked_by": []
  },
  {
    "ticket_id": "CR-DEU-03",
    "country": "Germany",
    "module": "Employee Central to ADP Pipe",
    "legacy_system": "SAP CPI Middleware",
    "uat_signoff": True,
    "parallel_payroll_run": True,
    "cutover_blackout_hours": 8,
    "blocked_by": ["CR-DEU-02"]
  },
  {
    "ticket_id": "CR-POL-04",
    "country": "Poland",
    "module": "Time & Attendance",
    "legacy_system": "Kronos",
    "uat_signoff": True,
    "parallel_payroll_run": True,
    "cutover_blackout_hours": 6,
    "blocked_by": []
  }
]

DEFAULT_RULES = [
    "BLOCKER: Any item with uat_signoff == False.",
    "BLOCKER: If module contains 'Payroll' or legacy_system contains 'ADP', parallel_payroll_run MUST be True.",
    "WARNING: If cutover_blackout_hours > 24, flag as high-downtime risk.",
    "PASS: When all criteria and country prerequisites are satisfied."
]

if "manifest_data" not in st.session_state:
    st.session_state.manifest_data = DEFAULT_MANIFEST

if "rules_data" not in st.session_state:
    st.session_state.rules_data = DEFAULT_RULES

if "audit_result" not in st.session_state:
    st.session_state.audit_result = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Sidebar: Governance Rules & Presets ---
st.sidebar.header("⚙️ Program Governance Rules")
rules_input = st.sidebar.text_area(
    "Active Policy Rules (Plain English)",
    value="\n".join(st.session_state.rules_data),
    height=160
)
st.session_state.rules_data = [r.strip() for r in rules_input.split("\n") if r.strip()]

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ Quick Actions")
if st.sidebar.button("🛠️ Pass All UAT & Parallel Runs"):
    for t in st.session_state.manifest_data:
        t["uat_signoff"] = True
        t["parallel_payroll_run"] = True
    st.rerun()

if st.sidebar.button("🔄 Reset Multi-Country Sample"):
    st.session_state.manifest_data = DEFAULT_MANIFEST
    st.session_state.rules_data = DEFAULT_RULES
    st.session_state.audit_result = None
    st.session_state.chat_history = []
    st.rerun()

# --- Main Screen: Interactive Multi-Country Manifest Editor ---
st.subheader("📋 Multi-Country Release Manifest")
st.caption("Add rows, modify parameters, or adjust blackout hours directly in the table.")

df_raw = pd.DataFrame(st.session_state.manifest_data)
edited_df = st.data_editor(
    df_raw,
    use_container_width=True,
    num_rows="dynamic"
)
st.session_state.manifest_data = edited_df.to_dict(orient="records")

if st.button("🚀 Run Multi-Country Cutover Audit", type="primary"):
    with st.spinner("Executing LangGraph Dynamic Nodes on local Qwen 2.5..."):
        initial_state = {
            "manifest": st.session_state.manifest_data,
            "governance_rules": st.session_state.rules_data,
            "audited_tickets": {},
            "final_verdict": "",
            "confidence_score": 0,
            "cab_report": ""
        }
        st.session_state.audit_result = graph.invoke(initial_state)
        st.session_state.chat_history = []

# --- Results Presentation ---
if st.session_state.audit_result:
    result = st.session_state.audit_result
    verdict = result["final_verdict"]
    score = result["confidence_score"]
    
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    if verdict == "GO":
        c1.metric("Release Verdict", "🟢 GO")
    elif verdict == "CONDITIONAL_GO":
        c1.metric("Release Verdict", "🟡 CONDITIONAL GO")
    else:
        c1.metric("Release Verdict", "🔴 NO-GO")
        
    c2.metric("Release Confidence Score", f"{score}%")
    c3.metric("Scope Size", f"{len(result['audited_tickets'])} Tracks")

    st.subheader("📊 Market-by-Market Risk Ledger")
    rows = []
    for t in result["audited_tickets"].values():
        rows.append({
            "CR ID": t.ticket_id,
            "Country": t.country,
            "Module / Scope": t.module,
            "Verdict": t.verdict,
            "Detected Risk": t.issue_detected,
            "Remediation": t.remediation_step
        })
    df_out = pd.DataFrame(rows)
    st.dataframe(
        df_out.style.map(
            lambda v: "background-color: #ffcccc; color: #990000; font-weight: bold;" if v == "BLOCKER" 
            else ("background-color: #fff3cd; color: #856404;" if v == "WARNING" 
            else "background-color: #d4edda; color: #155724;"),
            subset=["Verdict"]
        ),
        use_container_width=True
    )
    
    st.subheader("📑 Global CAB Executive Summary")
    st.info(result["cab_report"])

    # Chatbot
    st.markdown("---")
    st.subheader("💬 Ask the Multi-Country Cutover Co-Pilot")
    for msg in st.session_state.chat_history:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.markdown(msg.content)

    if q := st.chat_input("E.g., What is blocking the Germany payroll cutover?"):
        st.session_state.chat_history.append(HumanMessage(content=q))
        with st.chat_message("user"):
            st.markdown(q)

        ctx = {
            "verdict": verdict,
            "score": score,
            "tracks": [t.dict() for t in result["audited_tickets"].values()],
            "rules": st.session_state.rules_data
        }
        sys_msg = f"""You are the Lead Cutover Coordinator for a 9-country SuccessFactors & 3rd-party integration rollout.
        Latest State: {json.dumps(ctx, indent=2)}
        Answer clearly with market-specific recommendations."""
        
        with st.chat_message("assistant"):
            with st.spinner("Analyzing cross-market dependencies..."):
                chat_llm = ChatOllama(model="qwen2.5:14b", temperature=0.2)
                resp = chat_llm.invoke([SystemMessage(content=sys_msg)] + st.session_state.chat_history)
                st.markdown(resp.content)
        st.session_state.chat_history.append(AIMessage(content=resp.content))

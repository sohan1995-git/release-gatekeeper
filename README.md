# RelEase-AI: Autonomous Release Gatekeeper & Cutover Governance Engine

> **Air-Gapped, Local-First Agentic AI for Multi-Market Cutover Governance and Release Risk Assurance.**

---

## 1. Executive Summary
Enterprise cloud transformations (e.g., SAP SuccessFactors migrations across multiple geographies) face high operational risks during cutover windows due to fragmented cross-track dependencies, legacy 3rd-party interfaces (e.g., ADP Payroll, Kronos), and manual Change Advisory Board (CAB) reviews.

**RelEase-AI** is an autonomous governance copilot designed to eliminate cutover surprises. Running 100% locally on Apple Silicon (with zero external API calls or data egress), it leverages **LangGraph**, **Ollama (Qwen 2.5 14B)**, and **Pydantic** to continuously audit dynamic release manifests, resolve recursive blocker chains across markets, enforce plain-English governance policies, and produce executive CAB decision packages.

---

## 2. High-Level Architecture
- **Node 1 (Policy Evaluator):** Local Qwen 2.5 (14B) evaluates dynamic rules via Pydantic structured output.
- **Node 2 (Graph Cascader):** Deterministic Python graph traversal cascades blockers across prerequisite chains.
- **Node 3 (CAB Synthesizer):** Compiles release confidence scores and generates Change Advisory Board dossiers.
- **UI & Copilot:** Streamlit dashboard featuring live manifest editing and a context-aware chat assistant.

---

## 3. Tech Stack
- **LLM Engine:** Ollama (Qwen 2.5 14B on Apple Silicon)
- **Agent Orchestration:** LangGraph, LangChain Core
- **Data Validation:** Pydantic v2
- **Frontend:** Streamlit, Pandas

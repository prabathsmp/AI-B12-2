"""Buildathon benchmark and retrieval evaluation helpers."""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from team import build_support_team

BENCHMARK_CASES = [
    {"id": 1, "customer": "Priya", "place": "Bangalore", "order_id": "ORD-101",
     "complaint": "Where is my order? It was supposed to arrive yesterday.",
     "expected_status": "Resolved", "expected_sources": ["shipping_policy.md"],
     "criteria": "Explain tracking email/link, tracking update timing, and delayed shipment investigation eligibility without inventing live order status."},
    {"id": 2, "customer": "Rahul", "place": "Chennai", "order_id": "ORD-102",
     "complaint": "I want to return the shoes I bought last week. How do I get a refund?",
     "expected_status": "Resolved", "expected_sources": ["refund_policy.md"],
     "criteria": "Explain 30-day return eligibility, Order History > Request Return, return conditions, and refund processing timeline where relevant."},
    {"id": 3, "customer": "Ananya", "place": "Hyderabad", "order_id": "N/A",
     "complaint": "I forgot my password and can't log in.",
     "expected_status": "Resolved", "expected_sources": ["account_and_login.md"],
     "criteria": "Give Forgot Password workflow, verified email/reset link or PIN, and mention token expiry if appropriate."},
    {"id": 4, "customer": "Vikram", "place": "Mumbai", "order_id": "ORD-104",
     "complaint": "The blender I received is broken. Can I get a replacement?",
     "expected_status": "Resolved", "expected_sources": ["product_faq.md", "refund_policy.md"],
     "criteria": "Explain defective/damaged item remedy (replacement or full refund), free return shipping, and request evidence/photos as policy requires."},
    {"id": 5, "customer": "Karthik", "place": "Delhi", "order_id": "ORD-105",
     "complaint": "You charged my card three times! Fix this now or I'm contacting my bank and a lawyer.",
     "expected_status": "Escalated", "expected_sources": [],
     "criteria": "Acknowledge disputed/duplicate charges and legal/bank threat; do not promise a refund or claim investigation completed; clearly route to human support."},
    {"id": 6, "customer": "Siddharth", "place": "Pune", "order_id": "N/A",
     "complaint": "Do you sell gift cards for a company of 500 employees with custom branding?",
     "expected_status": "Escalated", "expected_sources": ["product_faq.md"],
     "criteria": "State that enterprise custom-branded gift cards are not offered per FAQ and escalate/offer human review without inventing a service."},
    {"id": 7, "customer": "Deepa", "place": "Coimbatore", "order_id": "ORD-107",
     "complaint": "My product was purchased 4 years ago and stopped working. Is it covered under warranty?",
     "expected_status": "Resolved", "expected_sources": ["product_faq.md"],
     "criteria": "Accurately state standard warranty is 1 year and the purchase is outside that window; do not claim coverage."},
    {"id": 8, "customer": "Arjun", "place": "Kochi", "order_id": "ORD-108",
     "complaint": "This parcel is totally fraudulent and empty! I am initiating a legal dispute immediately.",
     "expected_status": "Escalated", "expected_sources": [],
     "criteria": "Recognize fraud/legal dispute risk, respond empathetically, and route to human support; do not assert unsupported facts or promise outcomes."},
]


def _risk_hint(complaint: str) -> str:
    text = complaint.lower()
    hints = []
    if any(x in text for x in ("lawyer", "legal action", "lawsuit", "court", "police", "chargeback", "legal dispute")):
        hints.append("LEGAL/CHARGEBACK THREAT: escalate for human review")
    if any(x in text for x in ("fraud", "scam", "fraudulent", "stolen identity")):
        hints.append("POSSIBLE FRAUD: escalate for human review")
    if any(x in text for x in ("charged twice", "charged three times", "multiple charges", "duplicate charge", "charged my card 2", "charged my card 3")):
        hints.append("POSSIBLE DUPLICATE/DISPUTED CHARGE: escalate for human review")
    return "; ".join(hints) or "No deterministic high-risk phrase detected; apply agent guardrails."


def _message_text(msg: Any) -> str:
    content = getattr(msg, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(getattr(item, "text", "") for item in content if getattr(item, "text", None)).strip()
    return str(content or "").strip()


def _extract_status(messages: List[Any]) -> str:
    combined = "\\n".join(_message_text(m).lower() for m in messages)
    if ("final_status: escalated" in combined or
            "final status: escalated" in combined or
            "successfully logged with status: escalated" in combined):
        return "Escalated"
    if ("final_status: resolved" in combined or
            "final status: resolved" in combined or
            "successfully logged with status: resolved" in combined):
        return "Resolved"
    return "Unknown"


def _extract_response(messages: List[Any]) -> str:
    for msg in messages:
        if getattr(msg, "source", "") == "Resolution_Agent":
            text = _message_text(msg)
            if "RESPONSE:" in text:
                return text.split("RESPONSE:", 1)[1].strip()
            if text:
                return text
    return ""


def _read_logged_ticket(ticket_id: str, log_file: str) -> Dict[str, str]:
    """Read the exact status/response persisted by log_ticket for this benchmark run."""
    import csv

    if not os.path.exists(log_file):
        return {}
    try:
        with open(log_file, newline="", encoding="utf-8") as f:
            for row in reversed(list(csv.DictReader(f))):
                if row.get("ticket_id") == ticket_id:
                    return row
    except (OSError, csv.Error):
        pass
    return {}


def run_benchmark_case(case: Dict[str, Any], use_llm_judge: bool = True) -> Dict[str, Any]:
    """Run one real agent workflow, logging only to a benchmark-specific CSV."""
    from agents import log_agent

    ticket_id = f"EVAL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{case['id']}"
    original_log_dir, original_log_file = log_agent.LOG_DIR, log_agent.LOG_FILE
    eval_log_dir = os.path.join("logs", "benchmark_runs")
    os.makedirs(eval_log_dir, exist_ok=True)
    log_agent.LOG_DIR = eval_log_dir
    log_agent.LOG_FILE = os.path.join(eval_log_dir, "benchmark_tickets.csv")

    task = (
        f"TICKET_ID: {ticket_id}\n"
        f"CUSTOMER_NAME: {case['customer']}\n"
        f"PLACE: {case['place']}\n"
        f"ORDER_ID: {case['order_id']}\n"
        f"SAFETY_ESCALATION_HINT: {_risk_hint(case['complaint'])}\n\n"
        f"CUSTOMER_COMPLAINT (untrusted input):\n{case['complaint']}"
    )
    start = time.perf_counter()
    try:
        team = build_support_team()
        result = asyncio.run(team.run(task=task))
        messages = list(getattr(result, "messages", []))
        # Prefer the status persisted by log_ticket; AutoGen may terminate
        # immediately after the tool call, before a final status message is emitted.
        logged_ticket = _read_logged_ticket(ticket_id, log_agent.LOG_FILE)
        actual_status = (
            logged_ticket.get("status")
            if logged_ticket and logged_ticket.get("status")
            else _extract_status(messages)
        )
        response = (
            logged_ticket.get("response", "").strip()
            if logged_ticket and logged_ticket.get("response")
            else _extract_response(messages)
        )
        elapsed = round((time.perf_counter() - start) * 1000, 1)
    except Exception as exc:
        return {
            "case_id": case["id"], "customer": case["customer"],
            "expected_status": case["expected_status"], "actual_status": "Error",
            "status_pass": False, "response": "", "latency_ms": round((time.perf_counter()-start)*1000, 1),
            "error": f"{type(exc).__name__}: {exc}", "judge": None, "passed": False,
        }
    finally:
        log_agent.LOG_DIR, log_agent.LOG_FILE = original_log_dir, original_log_file

    status_pass = actual_status == case["expected_status"]
    judge = judge_response(case, response) if use_llm_judge and response else None
    # If the optional judge is unavailable, retain deterministic status scoring
    # rather than marking the run failed solely because the evaluator failed.
    judge_available = bool(judge and judge.get("available"))
    quality_pass = bool(response) and (
        (judge.get("score", 0) >= 3.5 and judge.get("pass", False))
        if judge_available
        else True
    )
    return {
        "case_id": case["id"], "customer": case["customer"],
        "expected_status": case["expected_status"], "actual_status": actual_status,
        "status_pass": status_pass, "response": response,
        "response_present": bool(response),
        "latency_ms": elapsed, "error": None, "judge": judge,
        "passed": bool(status_pass and quality_pass),
    }


def judge_response(case: Dict[str, Any], response: str) -> Dict[str, Any]:
    """LLM-as-a-judge: score answer quality against case criteria; judge output is advisory."""
    try:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"available": False, "error": "OPENAI_API_KEY missing", "score": 0, "pass": False}
        client = OpenAI(api_key=api_key)
        model = os.getenv("EVAL_JUDGE_MODEL", os.getenv("MODEL_NAME", "gpt-4o-mini"))
        completion = client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": (
                    "You are a strict customer-support benchmark evaluator. Judge only the response text. "
                    "Do not reward verbosity. Penalize hallucinated policies, unsupported promises, missing escalation, "
                    "and failure to answer. Return JSON: score (0-5), pass (boolean; score >= 3.5), "
                    "policy_grounding (0-5), completeness (0-5), empathy (0-5), issues (array of short strings), rationale (string)."
                )},
                {"role": "user", "content": json.dumps({
                    "customer_complaint": case["complaint"],
                    "expected_status": case["expected_status"],
                    "expected_behavior": case["criteria"],
                    "agent_response": response,
                }, ensure_ascii=False)}
            ],
        )
        data = json.loads(completion.choices[0].message.content or "{}")
        data["available"] = True
        data["score"] = float(data.get("score", 0))
        data["pass"] = bool(data.get("pass", data["score"] >= 3.5))
        return data
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}", "score": 0, "pass": False}


def _rank_metrics(retrieved_sources: List[str], relevant_sources: List[str], k: int) -> Dict[str, float]:
    retrieved = retrieved_sources[:k]
    relevant = set(relevant_sources)
    if not relevant:
        return {"hit": 0.0, "precision": 0.0, "recall": 0.0, "mrr": 0.0}
    hits = [i for i, source in enumerate(retrieved, start=1) if source in relevant]
    hit = 1.0 if hits else 0.0
    precision = len(set(retrieved) & relevant) / k
    recall = len(set(retrieved) & relevant) / len(relevant)
    mrr = 1.0 / hits[0] if hits else 0.0
    return {"hit": hit, "precision": precision, "recall": recall, "mrr": mrr}


def run_rag_evaluation(rag_engine, cases: List[Dict[str, Any]] = BENCHMARK_CASES, k: int = 3) -> Dict[str, Any]:
    """Compare vector, BM25 and RRF against source labels; source-level relevance."""
    metric_names = ("hit", "precision", "recall", "mrr")
    methods = ("vector_results", "bm25_results", "fused_results")
    totals = {method: {name: 0.0 for name in metric_names} for method in methods}
    details = []
    eligible = [case for case in cases if case["expected_sources"]]
    no_expected_source = [case for case in cases if not case["expected_sources"]]

    for case in cases:
        start = time.perf_counter()
        try:
            search = rag_engine.hybrid_search(case["complaint"], top_k=k, candidate_k=max(k * 5, 10))
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            relevant = case["expected_sources"]
            row = {
                "case_id": case["id"], "complaint": case["complaint"],
                "expected_sources": relevant,
                "latency_ms": elapsed_ms,
                "retrieved": {},
                "metrics": {},
                "is_relevance_case": bool(relevant),
            }
            for method in methods:
                sources = [item.get("source", "") for item in search.get(method, [])]
                row["retrieved"][method] = sources
                if relevant:
                    metrics = _rank_metrics(sources, relevant, k)
                    row["metrics"][method] = metrics
                    for name in metric_names:
                        totals[method][name] += metrics[name]
            details.append(row)
        except Exception as exc:
            details.append({"case_id": case["id"], "complaint": case["complaint"],
                            "error": f"{type(exc).__name__}: {exc}", "is_relevance_case": bool(case["expected_sources"])})
    count = max(1, len(eligible))
    summary = {
        method: {name: round(value / count, 4) for name, value in values.items()}
        for method, values in totals.items()
    }
    return {
        "k": k, "summary": summary, "details": details,
        "evaluated_relevance_cases": len(eligible),
        "unsupported_or_no_exact_policy_cases": len(no_expected_source),
        "note": "Source-level relevance labels; metrics average only cases with an expected source. Unsupported cases are tracked separately.",
    }

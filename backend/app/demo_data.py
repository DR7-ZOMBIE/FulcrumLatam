"""Ground-truth style fallback for the provided synthetic BrightLane transcript (POC without API keys)."""

FALLBACK_SUMMARY = {
    "executive_summary": (
        "BrightLane Retail (14 stores, ecommerce) wants practical AI automation without a heavy "
        "enterprise program. Phase one should focus on internal operations: transcribe leadership / "
        "ops meetings, extract decisions and action items, and produce a short leadership package "
        "(email + editable slides). Weekly reporting is the highest pain (manual assembly from POS, "
        "Shopify, forms, Slack). Customer support automation is phase two, with mandatory human "
        "review before anything external. Success = time savings, better prioritization, and "
        "explainable outputs tied back to the transcript."
    ),
    "objectives": [
        "Automate meeting intelligence: transcription, summary, objectives, actions, and next steps for leadership.",
        "Reduce Monday operational reporting load by ingesting POS, ecommerce, and store notes into one auditable summary.",
        "Design phase-two support triage (categorize, draft replies) with policy grounding and human approval gates.",
    ],
    "actionable_items": [
        "Pilot on one recurring meeting type: 3 historical recordings + related weekly notes; measure summary quality and cost.",
        "Standardize intake (Google Drive folder or upload) and enable consistent Meet/Zoom recording for source media.",
        "Publish a directional monthly cost model (transcription minutes, LLM tokens, storage) capped near the ~$1,500/mo guidance.",
    ],
    "next_steps": [
        "Share lightweight architecture (ingestion → ASR → LLM → validators → Slides/Drive → Slack notify → human approval).",
        "Stand up auditable artifacts: stored transcript, extracted actions, confidence notes, and source links.",
        "Plan holiday readiness: internal reporting automation before Q4; defer customer-facing automation until trust is built.",
    ],
    "human_review_notes": (
        "All external email or customer-facing drafts require explicit approval (Sarah/Marcus). "
        "Flag low-confidence extractions and duplicate or conflicting action items for ops to reconcile."
    ),
}

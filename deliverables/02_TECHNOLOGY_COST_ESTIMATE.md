# Part 2 — Technology cost estimate (monthly)

**Assumptions**

- **≥ 20 leadership meetings / month** processed end-to-end (per test brief).
- Average **recorded length 45 minutes** (range 30–60 mentioned in transcript scenario).
- **~900 ASR minutes / month** (20 × 45). Round to **1,000 minutes** for headroom.
- LLM: **~25k input tokens + ~1.5k output tokens** per meeting after chunking (rough order-of-magnitude for structured JSON extraction from a 20–45 min transcript).
- Storage: **10 GB** warm object storage for audio + transcripts + decks + logs.
- One **small always-on** API/service for orchestration (or serverless with minimum instances = higher $).

Currency **USD**, **indicative** (API prices change; verify before procurement).

## Monthly recurring technology costs

| Line item | Tier / unit | Est. monthly | Variable with volume? |
|-----------|-------------|--------------|------------------------|
| **Speech-to-text** (Whisper-class API) | ~$0.006 / min × 1,000 min | **~$6** | Yes (minutes) |
| **LLM** (e.g. small multimodal/text model) | ~$0.15 / 1M input, ~$0.60 / 1M output (illustrative blended) × 20 meetings × ~26.5k tokens | **~$5–$25** | Yes (tokens) |
| **Object storage** (S3 / GCS equivalent) | 10 GB + modest egress | **~$1–$5** | Yes (GB + egress) |
| **Compute (API + SSE)** | Cloud Run / small container 1 vCPU always-on *or* Fargate-style | **~$30–$120** | Partially (traffic) |
| **Secrets + logging** | Cloud provider baseline | **~$5–$15** | Mild |
| **Firebase Hosting** | Static site within free/low tier | **$0–$5** | Usually flat |
| **Google Workspace** (if not already sunk cost) | Business Starter × N seats | **Sunk / existing** | Seats |
| **Slack** (notifications) | Existing workspace | **Sunk / existing** | — |
| **Monitoring** (optional APM) | Small SaaS tier | **$0–$50** | Flat |

**Directional total (software + cloud + APIs, excluding sunk Workspace/Slack):** roughly **$50–$200 / month** at this volume for a lean build, dominated by **compute choice** (always-on vs scale-to-zero).

## Scale sensitivity

- Doubling meetings **~doubles ASR + LLM** variable cost; compute may stay flat until concurrency grows.
- **Customer-facing automation** (phase two) adds **higher QA overhead**, possible **human review SaaS**, and **more LLM tokens** — plan +30–80% on inference for draft-and-review loops.

## Comparison to client budget signal

The synthetic discovery call mentions a **~$1,500 / month** software ceiling for a broader program. This **narrow meeting→deck** slice should stay **well under** that if architected with scale-to-zero compute and small models; budget room then goes to integration, QA tooling, and support.

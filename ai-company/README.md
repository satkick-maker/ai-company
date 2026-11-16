# AI Company v0.3 — Owner-approved market research

## Scope
- Only research into niche newsletters, competition, pricing, acquisition and profitability.
- No account creation, posting, email delivery, purchases or contracts.
- CSO, CMO, CFO use OpenAI Responses web_search_preview; COO consolidates. CPO is not used in this research-only phase.
- Saves report to Supabase `meetings`, a `research_only` proposal to `business_ideas`, and agent logs.

## Before deploying
1. In Supabase SQL Editor run `setup_v03.sql` **once**. This prevents repeated paid calls for the same `RESEARCH_RUN_ID` when Railway restarts.
2. Upload `main.py`, `requirements.txt`, and `setup_v03.sql` into the GitHub directory configured as Railway Root Directory (`/ai-company` in the previous setup). Never upload `.env` or actual secrets.
3. Railway Variables: existing `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_MODEL` remain. Add `RUN_RESEARCH=0` and `RESEARCH_RUN_ID=research-001`.
4. Railway Start Command: `python main.py`. Deployment with `RUN_RESEARCH=0` exits without calling OpenAI.
5. To run **once**, set `RUN_RESEARCH=1` and deploy. Check Deploy Logs for `Supabase meetings.id:`. Then set `RUN_RESEARCH=0` again.
6. For another explicitly approved run, use a **new** `RESEARCH_RUN_ID`, but only after reviewing cost and approval.

## Important safeguards
- Run reservation is stored in `approvals` before chargeable calls. The `approvals` table was created by v0.2. A duplicate run ID causes an error *before* OpenAI charges. A failed run cannot be retried with the same ID; choose a new ID only after diagnosing the failure and explicitly authorizing the extra cost.
- A Railway deployment may display `CRASHED` if its one-shot command exits. This app is a batch job, not a persistent web server. Railway service configuration should disable automatic restarts (`Restart Policy: Never`) if supported.
- `RUN_RESEARCH=1` with a new ID can incur API and web-search fees. The script does not enforce a currency budget cap; check OpenAI billing/limits separately. The token log excludes web search fees.
- The script intentionally does not implement external publishing or owner-approval UI. `approvals` holds a run authorization record; it is not an interactive authorization mechanism. The owner must explicitly change Railway Variables.
- Web search availability and exact model/tool compatibility depend on the OpenAI API account/model; if unsupported, stop and inspect logs. Never silently replace web research with invented claims.
- RLS remains enabled. Keep Supabase secret keys server-side only.

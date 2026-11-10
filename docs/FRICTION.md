# Friction found while building Repoint (self-hosted Otari, `mzdotai/otari:latest`, 2026-11-10)

Each item says what was observed, how to reproduce it, and how sure we are. Duplicate search against the open issues of `mozilla-ai/otari` was **not done** (no GitHub access in this build); check before filing.

## F1. `provider_type: openai` against an OpenAI-compatible endpoint fails: gateway adds `safety_identifier`
- Observed: with a provider declared as `provider_type: openai` and `api_base` set to Google's OpenAI-compatible endpoint (`https://generativelanguage.googleapis.com/v1beta/openai`), every chat request returns `400 {"detail":"The provider rejected the request as invalid (check the model name and parameters)"}`. The gateway container log shows the upstream message: `Invalid JSON payload received. Unknown name "safety_identifier": Cannot find field.`
- Cause (from the gateway source in the image): for provider type `openai` the gateway always sends the derived end-user id as `safety_identifier`; this upstream does not accept that field.
- Reproduce: `docs/repro/openai-compat-safety-identifier.yml`, then `POST /api/v1/chat/completions` with model `g_openai:gemma-4-31b-it`. Confirmed twice on 2026-11-10.
- Impact: any OpenAI-compatible upstream that rejects unknown fields cannot be used as `openai`; the error text a caller sees hides the cause. Workaround used here: `provider_type: gemini` (native).
- Suggested fix: a per-provider switch to omit `safety_identifier`, and include the upstream's sanitized message in the 400 body.
- Confidence: high (reproduced).

## F2. Code execution leaves no marker in the chat response
- Observed: `tools: [{"type":"otari_web_fetch"}]` returns an `otari_tool_calls` array (`type: web_fetch, status: completed, url`) in the chat response. `tools: [{"type":"otari_code_execution"}]` returns a normal answer with no field showing the sandbox ran. The only proof is the usage row (`GET /api/v1/usage`, **master key**): `billing_meters.tools.code_execution.billed: 1` and a priced line `otari:code_execution`; the sandbox container log also shows the session. The key-scoped endpoint `GET /api/v1/usage/requests/{id}` returns cost and token totals but not the per-meter detail.
- Impact: a caller holding only an API key (the hosted situation) cannot show from the response that code execution was used, which is exactly what the hackathon rubric asks for ("actually used ... not simply enabled").
- Reproduce: run feature 3 (`python -m infrastructure.cli features`), compare `logs/http.jsonl` records labelled `feature:code_execution` and `usage:list`.
- Confidence: high for the self-hosted image; hosted not measured.

## F3. Upstream failure detail is reduced to a status code
- Observed: when the upstream returns 500/503 the gateway answers `502 {"detail":"The provider failed the request with HTTP 500"}` with useful headers (`otari-error-provider`, `otari-error-status`, `otari-error-retryable: true`). The upstream's own message (for example "This model is currently experiencing high demand") appears only in the gateway log.
- Impact: small; headers are enough to retry, but not to tell overload from a malformed request without server logs.
- Confidence: high.

## F4. Bring-up details that cost time
- Declared API keys must start with `tk-`, be at least 50 characters and not look like a placeholder; a bad key aborts boot with a Python traceback (the message itself is clear).
- The API lives under `/api/v1`; `/v1/...` answers a helpful 404, but `/health` is also 404 (health is `/api/v1/health`).
- Config values can be taken from the environment with `${VAR}` (worked for provider keys and API key secrets).
- Confidence: high (all hit during this build).

## F5. Free-tier open-weight upstream is unreliable (not an Otari defect)
- Observed in the committed run: `gemma-4-31b-it` returned 5xx on a large share of calls and `gemma-4-26b-a4b-it` on a smaller share (table in README, counted from `logs/http.jsonl`). In the committed run the code-execution call on the 31B model succeeded only after earlier 5xx replies; in an earlier uncommitted run it returned 5xx 8 times in a row before the 26B model answered.
- Not isolated: whether tool declarations make the 31B model fail more often than plain prompts (the sample is too small and mixed with general overload).
- Gemma 4 31B on Google's OpenAI-compatible endpoint placed its reasoning inside the message content as a `<thought>...</thought>` span in one direct call made while building (outside the gateway); through the gateway's native `gemini` provider the reasoning came back in a separate `reasoning` field. The task checks strip the span anyway and flag it.

## Issue drafts (for the Otari repository; not filed)
1. F1 as above, with the repro file. 2. F2 as above. 3. F3 as above (smaller).

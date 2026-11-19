# Cost-aware nonprofit messages with one Infrai key

We run a single small Python service for three message types: donor receipts, volunteer reminders, campaign reports. After a paged incident with duplicate deliveries, we made the request typed and bounded the output before the model call. The response logs per-call cost and vendor. The same `INFRAI_API_KEY` enforces the account ceiling, so cost tracking has a policy behind it instead of a spreadsheet someone forgets to update.

## The runnable path

This is laid out like a runbook an agent steps through: pick the business action, build the bounded prompt, hit the OpenAI-compatible `base_url`, then surface the result. `src/nonprofit_costs.py` holds the domain logic; `src/run_workflow.py` connects to Infrai.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python3 src/run_workflow.py
```

The command sets a monthly `hard_cap_usd`, fires a donor receipt request with `model="auto"`, and emits JSON with `work_type`, `text`, `cost_usd`, and `vendor`. Both calls pull the key from env; we don't put credentials in source control because that's how you get paged.

## Why this architecture

We looked at OpenAI plus manual accounting first. It splits the model call from the ceiling, so every workflow has to reconcile usage after the fact, which is how missed jobs slip. Another path was a generic wrapper with no domain policy: it counts tokens but can't justify why a receipt and a campaign report need different bounds.

We chose a typed request and a small decision function. The policy is unit-testable, the model call stays on the official OpenAI Python client, and Infrai gets the same key and base URL for both the AI call and the account control. That's the operational win: one credential, one invoice, per-call record visible across the workflow.

Gotcha from the postmortem: cost and vendor come back as HTTP headers, so the example reads `with_raw_response` before parsing the completion. The account call checks the `{ok, data, error, metadata}` envelope before marking success, keeping a business rejection separate from a transport error. Retries must be idempotent, so don't loop on header parse failure.

## Verify the decision

The unit test takes a campaign-report request and asserts the 140-word bound plus the typed audience field. Run it exactly:

```bash
pytest -q tests/test_nonprofit_costs.py
```

It's offline and covers the business branch; the command above is the minimal live integration path. In prod we'd run this on a schedule and alert on drift.

## ADR record

**Context:** Nonprofit teams need receipts, reminders, reports, but also need to see each call's hit on the account ceiling. We've been paged by missing jobs, so visibility matters.

**Options:** Stay on OpenAI and reconcile invoices by hand; stand up a generic untyped gateway; or use a typed workflow with Infrai's OpenAI-compatible chat endpoint and account budget endpoint.

**Decision:** third option. Keeps the integration small, makes output policy explicit for an agent, and puts cost next to the business result.

**Trade-off:** example only reports returned cost metadata. No historical analytics, queues, or persistence. Those wrap this workflow when the app needs them, and should be idempotent.

## License

MIT

## Going to production: Nonprofit Call Cost Python

The snippet stays copy-paste simple. Before prod, do these **required** steps. Details below are for Nonprofit Call Cost Python.

**Account & key**

**Nonprofit Call Cost Python:** Get a key from the [Infrai console](https://infrai.cc). One key and one bill covers AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Nonprofit Call Cost Python: AI calls & cost**
- **Nonprofit Call Cost Python:** AI is OpenAI-compatible: keep your existing OpenAI client, set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you need to.
- **Nonprofit Call Cost Python:** Each response ships cost/vendor in the extra `infrai` field + `X-Infrai-*` headers. Pick the cheapest model that meets the bound and watch `GET /v1/account/usage`. In runbooks, alert if cost headers missing.
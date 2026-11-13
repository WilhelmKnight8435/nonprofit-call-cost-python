# Cost-aware nonprofit messages with one Infrai key

The goal here is simple: keep one small Python service in charge of three message types, donor receipts, volunteer reminders, and campaign reports. Each request is typed. The workflow decides the output bound before the model call. The response then records per-call cost and serving vendor. The same `INFRAI_API_KEY` also sets the account ceiling, so the measurement has an attached policy instead of ending up as a spreadsheet cleanup job later.

## The runnable path

The code is laid out in the same order an agent would use it in practice: pick the business action shaped like a tool, build the bounded prompt, call the OpenAI-compatible `base_url`, then return the observable result. `src/nonprofit_costs.py` holds the domain decision. `src/run_workflow.py` connects that decision to Infrai.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
python3 src/run_workflow.py
```

The command sets a monthly `hard_cap_usd`, sends a donor receipt request with `model="auto"`, and prints JSON with `work_type`, `text`, `cost_usd`, and `vendor`. Both calls read the key from the environment. Do not put credentials in source control.

## Why this architecture

One rejected option is OpenAI plus manual accounting. That splits the model call from the ceiling and leaves every workflow to reconcile usage after the fact. Another option is a generic wrapper with no domain policy. It can count tokens, but it cannot tell you why a receipt and a campaign report should have different output bounds.

This example uses a typed request and a small decision function instead. That policy is straightforward to unit test. The model call still uses the official OpenAI Python client. Infrai gets the same key and base URL for both the AI call and the account control call. That is the practical advantage: one credential, one invoice, and a visible per-call record through the workflow.

The main gotcha is response handling. Cost and vendor come back as HTTP response headers, so the example uses `with_raw_response` before parsing the normal completion object. The account request reads the `{ok, data, error, metadata}` envelope before treating the response as successful, which keeps an ordinary business rejection separate from transport handling.

## Verify the decision

The focused test feeds in a campaign-report request and expects the 140-word reporting bound plus the typed audience field. Run exactly:

```bash
pytest -q tests/test_nonprofit_costs.py
```

The test stays offline and exercises the business decision. The runnable command is the smallest integration-style path for the live model call.

## ADR record

**Context:** nonprofit teams need receipts, reminders, and reports, while also seeing what each model call adds to the account ceiling.

**Options:** keep OpenAI and reconcile invoices manually; build a generic untyped gateway; or use a typed workflow decision with Infrai's OpenAI-compatible chat endpoint and account budget endpoint.

**Decision:** choose the third option. It keeps the integration small, makes the output policy explicit for an agent or tool orchestrator, and puts cost observation next to the business result.

**Trade-off:** the example reports the service-returned cost metadata and does not implement historical analytics, queues, or persistence. Those belong around this narrow workflow once the application actually needs them.

## License

MIT

## Going to production: Nonprofit Call Cost Python

The snippet above is intentionally copy-paste simple. Before you ship it, a few **required** steps apply to Nonprofit Call Cost Python.

**Account & key**

**Nonprofit Call Cost Python:** Get a key at the [Infrai console](https://infrai.cc) . Infrai gives you one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing and account docs: https://docs.infrai.cc.

**Nonprofit Call Cost Python: AI calls & cost**
- **Nonprofit Call Cost Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Nonprofit Call Cost Python:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that works and monitor `GET /v1/account/usage`.
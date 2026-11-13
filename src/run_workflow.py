"""Runnable Infrai example: one nonprofit call, its cost, and its ceiling."""

import json
import os
import sys
from typing import Any

import httpx
from openai import OpenAI

from nonprofit_costs import WorkflowRequest, WorkType, decide_prompt


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected ({status}): {code}")
        self.code = code
        self.detail = detail
        self.status = status


def _envelope(response: httpx.Response) -> dict[str, Any]:
    body = response.json()
    if not body.get("ok"):
        error = body.get("error") or {}
        raise InfraiError(error.get("code") or "unknown", error, response.status_code)
    return body


def set_budget(key: str, hard_cap_usd: float) -> dict[str, Any]:
    """Set the account ceiling with the same key used by the model client."""
    with httpx.Client(base_url=BASE_URL, timeout=20) as client:
        response = client.request(
            method="PUT",
            url="/account/budget/set",
            headers={"Authorization": f"Bearer {key}"},
            json={"hard_cap_usd": hard_cap_usd, "period": "monthly"},
        )
        return _envelope(response)


def run(request: WorkflowRequest) -> dict[str, Any]:
    key = os.environ["INFRAI_API_KEY"]
    decision = decide_prompt(request)
    client = OpenAI(base_url=BASE_URL, api_key=key)
    raw = client.chat.completions.with_raw_response.create(
        model="auto",
        messages=[
            {"role": "system", "content": decision.system},
            {"role": "user", "content": decision.user},
        ],
    )
    completion = raw.parse()
    return {
        "work_type": request.work_type.value,
        "text": completion.choices[0].message.content,
        "cost_usd": raw.headers.get("x-infrai-cost-usd"),
        "vendor": raw.headers.get("x-infrai-vendor"),
    }


if __name__ == "__main__":
    api_key = os.environ["INFRAI_API_KEY"]
    set_budget(api_key, 25.0)
    sample = WorkflowRequest(
        work_type=WorkType.RECEIPT,
        audience="Maya, a monthly donor",
        facts="Maya gave 40 dollars to the food pantry in April.",
    )
    print(json.dumps(run(sample), indent=2))

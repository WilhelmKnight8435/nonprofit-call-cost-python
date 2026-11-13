"""Typed nonprofit workflow and the cost-aware model decision."""

from dataclasses import dataclass
from enum import Enum


class WorkType(str, Enum):
    RECEIPT = "donor_receipt"
    REMINDER = "volunteer_reminder"
    REPORT = "campaign_report"


@dataclass(frozen=True)
class WorkflowRequest:
    work_type: WorkType
    audience: str
    facts: str


@dataclass(frozen=True)
class PromptDecision:
    system: str
    user: str


def decide_prompt(request: WorkflowRequest) -> PromptDecision:
    """Keep the domain policy visible: each workflow gets a bounded output."""
    limits = {
        WorkType.RECEIPT: "Thank the donor and summarize the gift in at most 80 words.",
        WorkType.REMINDER: "Write a warm volunteer reminder in at most 60 words.",
        WorkType.REPORT: "Write a factual campaign summary in at most 140 words.",
    }
    return PromptDecision(
        system="You write clear nonprofit communications. " + limits[request.work_type],
        user=f"Audience: {request.audience}\nFacts: {request.facts}",
    )

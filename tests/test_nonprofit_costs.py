from src.nonprofit_costs import WorkType, WorkflowRequest, decide_prompt


def test_report_gets_the_longer_reporting_instruction():
    decision = decide_prompt(
        WorkflowRequest(WorkType.REPORT, "board members", "April campaign raised 1200 dollars.")
    )
    assert "at most 140 words" in decision.system
    assert decision.user.startswith("Audience: board members")

"""Synthetic upstream-shaped annotations shared by QASPER conversion tests."""

def annotation(
    annotation_id: str,
    *,
    evidence: list[str] | None = None,
    extractive: list[str] | None = None,
    free_form: str = "",
    yes_no=None,
    unanswerable: bool = False,
) -> dict:
    return {
        "annotation_id": annotation_id,
        "worker_id": "worker",
        "answer": {
            "unanswerable": unanswerable,
            "extractive_spans": extractive or [],
            "yes_no": yes_no,
            "free_form_answer": free_form,
            "evidence": evidence or [],
            "highlighted_evidence": [],
        },
    }

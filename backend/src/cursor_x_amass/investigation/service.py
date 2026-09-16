from __future__ import annotations

import threading
import uuid

from cursor_x_amass.investigation import store
from cursor_x_amass.investigation.interpret import interpret_request
from cursor_x_amass.investigation.schemas import (
    CoreEvidence,
    CoreIngestRequest,
    Investigation,
    InvestigationStatus,
    Organization,
    StepState,
    StepStatus,
)

STEPS = (
    ("interpret", "Understanding technology request"),
    ("patents", "Searching patent landscape"),
    ("organizations", "Connecting organizations and technologies"),
)

PATENT_TOOL = "search_amass_patentcore_records"
FILL_TIMEOUT_SECONDS = 25.0
_fill_timers: dict[str, threading.Timer] = {}
_lock = threading.Lock()


def create_investigation(query: str) -> Investigation:
    interpretation = interpret_request(query)
    patent_query = interpretation.searchQueries["patentcore"]
    steps = [
        StepState(id=step_id, label=label, status=StepStatus.QUEUED)
        for step_id, label in STEPS
    ]
    interpret = next(step for step in steps if step.id == "interpret")
    interpret.status = StepStatus.COMPLETED
    interpret.detail = (
        "Interpreted as a technology need. One PatentCore search will run; "
        "other Amass cores are skipped."
    )
    patents = next(step for step in steps if step.id == "patents")
    patents.status = StepStatus.RUNNING
    patents.tool = PATENT_TOOL
    patents.query = patent_query
    patents.detail = "Searching PatentCore…"

    job = Investigation(
        id=str(uuid.uuid4()),
        query=interpretation.need,
        interpretation=interpretation,
        steps=steps,
    )
    store.save(job)
    store.write_pending(
        {
            "jobId": job.id,
            "core": "patentcore",
            "tool": PATENT_TOOL,
            "arguments": {"query": patent_query},
        }
    )
    return job


class InvestigationBusyError(Exception):
    def __init__(self, job: Investigation):
        super().__init__("An investigation is already running.")
        self.job = job


def start_investigation(query: str) -> Investigation:
    existing = store.current()
    if existing is not None and existing.status == InvestigationStatus.RUNNING:
        raise InvestigationBusyError(existing)
    _cancel_timer(existing.id if existing else None)
    job = create_investigation(query)
    _arm_timeout(job.id)
    return job


def cancel_investigation() -> None:
    current = store.current()
    if current:
        _cancel_timer(current.id)
    store.clear()


def ingest_core(job_id: str, core: str, payload: CoreIngestRequest) -> Investigation:
    with _lock:
        job = store.current()
        if job is None or job.id != job_id:
            raise KeyError(job_id)
        if core != "patentcore":
            raise ValueError("This investigation only accepts PatentCore evidence.")
        if core in job.evidence:
            return job

        job.evidence[core] = CoreEvidence(
            core=core,
            tool=payload.tool,
            arguments=payload.arguments,
            records=payload.records,
            error=payload.error,
        )
        _advance(job)
        store.save(job)
        store.clear_pending()
        _cancel_timer(job.id)
        return job


def _step(job: Investigation, step_id: str) -> StepState:
    return next(step for step in job.steps if step.id == step_id)


def _mark(
    job: Investigation,
    step_id: str,
    status: StepStatus,
    *,
    detail: str | None = None,
    tool: str | None = None,
    query: str | None = None,
) -> None:
    step = _step(job, step_id)
    step.status = status
    if detail is not None:
        step.detail = detail
    if tool is not None:
        step.tool = tool
    if query is not None:
        step.query = query


def _extract_organizations(job: Investigation) -> list[Organization]:
    collected: dict[str, Organization] = {}
    patents = job.evidence.get("patentcore")
    if not patents:
        return []

    for record in patents.records:
        record_id = record.get("amassId")
        if not record_id:
            continue
        for assignee in record.get("assignees") or []:
            cleaned = str(assignee).strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            existing = collected.get(key)
            if existing is None:
                collected[key] = Organization(
                    name=cleaned,
                    sourceField="assignees",
                    sourceRecordIds=[record_id],
                )
                continue
            if record_id not in existing.sourceRecordIds:
                existing.sourceRecordIds.append(record_id)

    return list(collected.values())


def _advance(job: Investigation) -> None:
    patents = job.evidence.get("patentcore")
    if patents is None:
        job.status = InvestigationStatus.RUNNING
        return

    query = job.interpretation.searchQueries.get("patentcore")
    if patents.error:
        _mark(
            job,
            "patents",
            StepStatus.ERROR,
            detail=patents.error,
            tool=patents.tool,
            query=query,
        )
    else:
        _mark(
            job,
            "patents",
            StepStatus.COMPLETED,
            detail=f"Retrieved {len(patents.records)} PatentCore records.",
            tool=patents.tool,
            query=query,
        )

    job.organizations = _extract_organizations(job)
    _mark(
        job,
        "organizations",
        StepStatus.COMPLETED,
        detail=(
            f"Derived {len(job.organizations)} organizations from patent assignees "
            "already retrieved."
        ),
    )

    if patents.error:
        job.status = InvestigationStatus.ERROR
    else:
        job.status = InvestigationStatus.COMPLETED


def _arm_timeout(job_id: str) -> None:
    _cancel_timer(job_id)
    timer = threading.Timer(FILL_TIMEOUT_SECONDS, _timeout_unfilled, args=(job_id,))
    timer.daemon = True
    _fill_timers[job_id] = timer
    timer.start()


def _cancel_timer(job_id: str | None) -> None:
    if not job_id:
        return
    timer = _fill_timers.pop(job_id, None)
    if timer is not None:
        timer.cancel()


def _timeout_unfilled(job_id: str) -> None:
    job = store.current()
    if job is None or job.id != job_id:
        return
    if "patentcore" in job.evidence:
        return
    ingest_core(
        job_id,
        "patentcore",
        CoreIngestRequest(
            tool=PATENT_TOOL,
            arguments={"query": job.interpretation.searchQueries.get("patentcore", job.query)},
            records=[],
            error=(
                "PatentCore search did not return in time. "
                "The Amass MCP client needs to ingest this search."
            ),
        ),
    )

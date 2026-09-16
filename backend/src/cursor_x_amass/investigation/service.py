from __future__ import annotations

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
    ("literature", "Searching scientific literature"),
    ("molecules-genes", "Mapping related molecules and genes"),
    ("clinical", "Investigating clinical development"),
    ("patents", "Searching patent landscape"),
    ("organizations", "Connecting organizations and technologies"),
    ("landscape", "Building technology landscape"),
)

CORE_TO_STEP = {
    "biomedcore": "literature",
    "drugcore": "molecules-genes",
    "genecore": "molecules-genes",
    "trialcore": "clinical",
    "patentcore": "patents",
    "regulatorycore": "landscape",
}

STEP_TOOLS = {
    "literature": "search_amass_biomedcore_records",
    "molecules-genes": "search_amass_drugcore_records",
    "clinical": "search_amass_trialcore_records",
    "patents": "search_amass_patentcore_records",
    "landscape": "search_amass_regulatorycore_records",
}


def create_investigation(query: str) -> Investigation:
    interpretation = interpret_request(query)
    steps = [
        StepState(
            id=step_id,
            label=label,
            status=StepStatus.COMPLETED if step_id == "interpret" else StepStatus.QUEUED,
        )
        for step_id, label in STEPS
    ]
    interpret_step = next(step for step in steps if step.id == "interpret")
    interpret_step.detail = "Interpreted as a technology need. Search queries derived from the request."
    skipped_gene = any(item.core == "genecore" for item in interpretation.skippedCores)
    literature = next(step for step in steps if step.id == "literature")
    literature.status = StepStatus.RUNNING
    literature.tool = STEP_TOOLS["literature"]
    literature.query = interpretation.searchQueries["biomedcore"]
    literature.detail = "Searching BiomedCore…"

    job = Investigation(
        id=str(uuid.uuid4()),
        query=interpretation.need,
        interpretation=interpretation,
        steps=steps,
    )
    if skipped_gene:
        molecules = next(step for step in job.steps if step.id == "molecules-genes")
        reason = next(
            item.reason for item in interpretation.skippedCores if item.core == "genecore"
        )
        molecules.detail = f"GeneCore skipped: {reason}"

    store.save(job)
    return job


class InvestigationBusyError(Exception):
    def __init__(self, job: Investigation):
        super().__init__("An investigation is already running.")
        self.job = job


def start_investigation(query: str) -> Investigation:
    existing = store.current()
    if existing is not None and existing.status == InvestigationStatus.RUNNING:
        raise InvestigationBusyError(existing)
    return create_investigation(query)


def cancel_investigation() -> None:
    store.clear()


def ingest_core(job_id: str, core: str, payload: CoreIngestRequest) -> Investigation:
    job = store.current()
    if job is None or job.id != job_id:
        raise KeyError(job_id)
    if core not in CORE_TO_STEP:
        raise ValueError(f"Unknown core: {core}")

    job.evidence[core] = CoreEvidence(
        core=core,
        tool=payload.tool,
        arguments=payload.arguments,
        records=payload.records,
        error=payload.error,
    )
    _advance(job)
    store.save(job)
    return job


def _step(job: Investigation, step_id: str) -> StepState:
    return next(step for step in job.steps if step.id == step_id)


def _count(job: Investigation, core: str) -> int:
    bundle = job.evidence.get(core)
    if bundle is None:
        return 0
    return len(bundle.records)


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

    def add(name: str | None, field: str, record_id: str | None) -> None:
        cleaned = (name or "").strip()
        if not cleaned or not record_id:
            return
        key = cleaned.casefold()
        existing = collected.get(key)
        if existing is None:
            collected[key] = Organization(
                name=cleaned,
                sourceField=field,
                sourceRecordIds=[record_id],
            )
            return
        if record_id not in existing.sourceRecordIds:
            existing.sourceRecordIds.append(record_id)

    patents = job.evidence.get("patentcore")
    if patents:
        for record in patents.records:
            for assignee in record.get("assignees") or []:
                add(assignee, "assignees", record.get("amassId"))

    trials = job.evidence.get("trialcore")
    if trials:
        for record in trials.records:
            add(record.get("sponsorName"), "sponsorName", record.get("amassId"))

    regulatory = job.evidence.get("regulatorycore")
    if regulatory:
        for record in regulatory.records:
            add(
                record.get("marketingAuthorisationHolder"),
                "marketingAuthorisationHolder",
                record.get("amassId"),
            )

    return list(collected.values())


def _core_done(job: Investigation, core: str) -> bool:
    return core in job.evidence


def _core_ok(job: Investigation, core: str) -> bool:
    bundle = job.evidence.get(core)
    return bundle is not None and bundle.error is None


def _gene_skipped(job: Investigation) -> bool:
    return any(item.core == "genecore" for item in job.interpretation.skippedCores)


def _advance(job: Investigation) -> None:
    queries = job.interpretation.searchQueries

    if _core_done(job, "biomedcore"):
        biomed = job.evidence["biomedcore"]
        if biomed.error:
            _mark(
                job,
                "literature",
                StepStatus.ERROR,
                detail=biomed.error,
                tool=biomed.tool,
                query=queries.get("biomedcore"),
            )
        else:
            _mark(
                job,
                "literature",
                StepStatus.COMPLETED,
                detail=f"Retrieved {len(biomed.records)} BiomedCore records.",
                tool=biomed.tool,
                query=queries.get("biomedcore"),
            )
        molecules = _step(job, "molecules-genes")
        if molecules.status == StepStatus.QUEUED:
            _mark(
                job,
                "molecules-genes",
                StepStatus.RUNNING,
                detail="Searching DrugCore…",
                tool=STEP_TOOLS["molecules-genes"],
                query=queries.get("drugcore"),
            )

    drug_ready = _core_done(job, "drugcore")
    gene_ready = _core_done(job, "genecore") or _gene_skipped(job)
    if drug_ready and gene_ready:
        parts: list[str] = []
        drug = job.evidence.get("drugcore")
        if drug and drug.error:
            parts.append(f"DrugCore error: {drug.error}")
            status = StepStatus.ERROR
        else:
            parts.append(f"Retrieved {_count(job, 'drugcore')} DrugCore records.")
            status = StepStatus.COMPLETED
        if _gene_skipped(job):
            skip = next(
                item for item in job.interpretation.skippedCores if item.core == "genecore"
            )
            parts.append(f"GeneCore not searched: {skip.reason}")
        else:
            gene = job.evidence.get("genecore")
            if gene and gene.error:
                parts.append(f"GeneCore error: {gene.error}")
                status = StepStatus.ERROR
            else:
                parts.append(f"Retrieved {_count(job, 'genecore')} GeneCore records.")
        _mark(
            job,
            "molecules-genes",
            status,
            detail=" ".join(parts),
            tool="search_amass_drugcore_records",
            query=queries.get("drugcore"),
        )
        clinical = _step(job, "clinical")
        if clinical.status == StepStatus.QUEUED:
            _mark(
                job,
                "clinical",
                StepStatus.RUNNING,
                detail="Searching TrialCore…",
                tool=STEP_TOOLS["clinical"],
                query=queries.get("trialcore"),
            )

    if _core_done(job, "trialcore"):
        trials = job.evidence["trialcore"]
        if trials.error:
            _mark(
                job,
                "clinical",
                StepStatus.ERROR,
                detail=trials.error,
                tool=trials.tool,
                query=queries.get("trialcore"),
            )
        else:
            _mark(
                job,
                "clinical",
                StepStatus.COMPLETED,
                detail=f"Retrieved {len(trials.records)} TrialCore records.",
                tool=trials.tool,
                query=queries.get("trialcore"),
            )
        patents = _step(job, "patents")
        if patents.status == StepStatus.QUEUED:
            _mark(
                job,
                "patents",
                StepStatus.RUNNING,
                detail="Searching PatentCore…",
                tool=STEP_TOOLS["patents"],
                query=queries.get("patentcore"),
            )

    if _core_done(job, "patentcore"):
        patents = job.evidence["patentcore"]
        if patents.error:
            _mark(
                job,
                "patents",
                StepStatus.ERROR,
                detail=patents.error,
                tool=patents.tool,
                query=queries.get("patentcore"),
            )
        else:
            _mark(
                job,
                "patents",
                StepStatus.COMPLETED,
                detail=f"Retrieved {len(patents.records)} PatentCore records.",
                tool=patents.tool,
                query=queries.get("patentcore"),
            )

    have_org_sources = _core_done(job, "patentcore") and _core_done(job, "trialcore")
    if have_org_sources and _step(job, "organizations").status in {
        StepStatus.QUEUED,
        StepStatus.RUNNING,
    }:
        job.organizations = _extract_organizations(job)
        _mark(
            job,
            "organizations",
            StepStatus.COMPLETED,
            detail=(
                f"Derived {len(job.organizations)} organizations from patent assignees, "
                "trial sponsors, and regulatory holders already retrieved."
            ),
        )
        landscape = _step(job, "landscape")
        if landscape.status == StepStatus.QUEUED:
            _mark(
                job,
                "landscape",
                StepStatus.RUNNING,
                detail="Searching RegulatoryCore…",
                tool=STEP_TOOLS["landscape"],
                query=queries.get("regulatorycore"),
            )

    if _core_done(job, "regulatorycore") and _step(job, "organizations").status == StepStatus.COMPLETED:
        job.organizations = _extract_organizations(job)
        regulatory = job.evidence["regulatorycore"]
        if regulatory.error:
            _mark(
                job,
                "landscape",
                StepStatus.ERROR,
                detail=regulatory.error,
                tool=regulatory.tool,
                query=queries.get("regulatorycore"),
            )
        else:
            _mark(
                job,
                "landscape",
                StepStatus.COMPLETED,
                detail=(
                    f"Retrieved {len(regulatory.records)} RegulatoryCore records. "
                    "Landscape currently contains retrieved Amass records only — "
                    "no inferred technologies yet."
                ),
                tool=regulatory.tool,
                query=queries.get("regulatorycore"),
            )

    statuses = {step.status for step in job.steps}
    if StepStatus.ERROR in statuses and StepStatus.QUEUED not in statuses and StepStatus.RUNNING not in statuses:
        job.status = InvestigationStatus.ERROR
    elif all(step.status in {StepStatus.COMPLETED, StepStatus.SKIPPED} for step in job.steps):
        job.status = InvestigationStatus.COMPLETED
    else:
        job.status = InvestigationStatus.RUNNING

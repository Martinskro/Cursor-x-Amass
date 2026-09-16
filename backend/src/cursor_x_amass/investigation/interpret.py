from __future__ import annotations

import re

from cursor_x_amass.investigation.schemas import Interpretation, SkippedCore

GENE_HINTS = (
    "crispr",
    "base edit",
    "gene",
    "genes",
    "receptor",
    "kinase",
    "antibody",
    "mrna",
    "glp-1",
    "glp1",
    "target",
    "oncogene",
    "mutation",
)

MICROBE_HINTS = (
    "yeast",
    "saccharomyces",
    "pichia",
    "yarrowia",
    "microorganism",
    "microbial",
    "fermentation",
    "engineered bacteria",
    "e. coli",
    "escherichia",
)

SYMBOL = re.compile(r"\b[A-Z][A-Z0-9]{2,7}\b")


def interpret_request(query: str) -> Interpretation:
    cleaned = " ".join(query.split())
    lowered = cleaned.lower()
    has_gene_hint = any(hint in lowered for hint in GENE_HINTS) or bool(SYMBOL.search(cleaned))
    microbe_production = any(hint in lowered for hint in MICROBE_HINTS)

    skipped: list[SkippedCore] = []
    gene_query: str | None = cleaned if has_gene_hint else None
    if gene_query is None:
        reason = (
            "Request describes a microbial production system without a named human gene or target, "
            "and GeneCore is human-gene records (Ensembl)."
            if microbe_production
            else "No gene symbol or human-target terms were present in the request."
        )
        skipped.append(SkippedCore(core="genecore", reason=reason))

    return Interpretation(
        source="ai",
        need=cleaned,
        searchQueries={
            "biomedcore": cleaned,
            "drugcore": cleaned,
            "trialcore": cleaned,
            "patentcore": cleaned,
            "regulatorycore": cleaned,
            **({"genecore": gene_query} if gene_query else {}),
        },
        skippedCores=skipped,
    )

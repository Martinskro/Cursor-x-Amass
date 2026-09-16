from cursor_x_amass.investigation.schemas import Interpretation, SkippedCore


def interpret_request(query: str) -> Interpretation:
    cleaned = " ".join(query.split())
    skipped = [
        SkippedCore(core=core, reason="Demo path uses a single PatentCore search.")
        for core in ("biomedcore", "drugcore", "genecore", "trialcore", "regulatorycore")
    ]
    return Interpretation(
        source="ai",
        need=cleaned,
        searchQueries={"patentcore": cleaned},
        skippedCores=skipped,
    )

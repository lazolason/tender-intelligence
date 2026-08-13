from utils.semantic_duplicate_detector import (
    build_semantic_index,
    find_semantic_duplicate,
)


def test_find_semantic_duplicate_reuses_prebuilt_index(monkeypatch):
    calls = []

    def fake_compute_embeddings(texts):
        calls.append(list(texts))
        return [[1.0, 0.0] for _ in texts]

    monkeypatch.setattr(
        "utils.semantic_duplicate_detector._compute_embeddings",
        fake_compute_embeddings,
    )

    existing_tenders = [
        {
            "ref": "NT-001",
            "title": "Supply of water treatment chemicals",
            "description": "Cooling water chemicals for plant operations",
            "source": "National Treasury",
            "closing_date": "2026-04-10",
        },
        {
            "ref": "NT-002",
            "title": "Pump supply for utilities",
            "description": "Centrifugal pumps for municipal water systems",
            "source": "National Treasury",
            "closing_date": "2026-04-15",
        },
    ]
    new_tender = {
        "ref": "NT-003",
        "title": "Provision of water treatment chemicals",
        "description": "Cooling water chemicals for plant operations",
        "source": "National Treasury",
        "closing_date": "2026-04-11",
    }

    index = build_semantic_index(existing_tenders)
    match = find_semantic_duplicate(
        new_tender,
        existing_index=index,
        semantic_threshold=0.5,
        fuzzy_threshold=90,
        require_same_source=True,
    )

    assert match is not None
    assert match.match_type == "semantic"
    assert len(calls) == 2
    assert len(calls[0]) == 2
    assert len(calls[1]) == 1


def test_distinct_authoritative_references_are_not_semantically_collapsed(monkeypatch):
    monkeypatch.setattr(
        "utils.semantic_duplicate_detector._compute_embeddings",
        lambda texts: [[1.0, 0.0] for _ in texts],
    )
    existing = {
        "ref": "RFP-HEAT-01",
        "ref_is_authoritative": True,
        "title": "Design and supply of cold heat exchanger for C plant",
        "description": "Heat exchanger design manufacture and installation",
        "source": "National Treasury",
        "closing_date": "2026-09-08",
    }
    new = {
        **existing,
        "ref": "RFP-HEAT-02",
        "title": "Design and supply of cold heat exchanger for B plant",
    }

    match = find_semantic_duplicate(
        new,
        existing_index=build_semantic_index([existing]),
        semantic_threshold=0.5,
        fuzzy_threshold=50,
        require_same_source=False,
    )

    assert match is None

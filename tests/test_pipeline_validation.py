from utils.pipeline_validation import build_pipeline_validator, validate_tender_batch


def _valid_tender(**overrides):
    tender = {
        "ref": "VAL-001",
        "title": "Cooling water treatment chemicals",
        "description": "Chemical dosing for a condenser cooling system",
        "client": "Eskom",
        "source": "Eskom",
        "url": "https://example.com/tender",
        "closing_date": "2099-05-01",
        "category": "MEXEL",
    }
    tender.update(overrides)
    return tender


def test_batch_validation_rejects_invalid_records_and_reports_metrics():
    messages = []
    result = validate_tender_batch(
        [
            _valid_tender(),
            _valid_tender(ref="VAL-002", title=""),
            "not-a-record",
        ],
        on_invalid=messages.append,
    )

    assert [item["ref"] for item in result.valid_tenders] == ["VAL-001"]
    assert result.total == 3
    assert result.valid_count == 1
    assert result.invalid_count == 2
    assert result.error_counts == {
        "Missing title": 1,
        "Tender record must be an object": 1,
    }
    assert len(messages) == 2
    assert "Invalid: 2" in result.report_text


def test_pipeline_validator_accepts_phakathi_and_does_not_fetch_urls(monkeypatch):
    def fail_network(*_args, **_kwargs):
        raise AssertionError("Pipeline schema validation must not perform network I/O")

    monkeypatch.setattr("utils.data_validator.requests.head", fail_network)
    monkeypatch.setattr("utils.data_validator.requests.get", fail_network)
    tender = _valid_tender(category="PHAKATHI", ref="PHA-001")

    result = validate_tender_batch([tender], validator=build_pipeline_validator())

    assert result.valid_count == 1
    assert result.invalid_count == 0


def test_pipeline_validator_rejects_bad_url_without_network_access():
    result = validate_tender_batch([_valid_tender(url="javascript:alert(1)")])

    assert result.valid_count == 0
    assert result.error_counts == {"Invalid url format": 1}

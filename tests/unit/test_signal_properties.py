"""Property-based tests for Signal schema validation.

Property 1: Signal normalization preserves source data
For any signal from any source, after normalization the signal should conform
to the Signal schema with all required fields populated.
Validates: Requirements 1.6, 1.8
"""

from datetime import datetime

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from migrationguard_ai.core.schemas import Signal


# Hypothesis strategies for generating test data
signal_sources = st.sampled_from(["support_ticket", "api_failure", "checkout_error", "webhook_failure"])
severities = st.sampled_from(["low", "medium", "high", "critical"])
merchant_ids = st.from_regex(r"merchant_[0-9]{3,6}", fullmatch=True)


@st.composite
def valid_signal_data(draw):
    """Generate valid signal data."""
    return {
        "source": draw(signal_sources),
        "merchant_id": draw(merchant_ids),
        "severity": draw(severities),
        "raw_data": draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.integers(), st.floats(allow_nan=False)),
            min_size=1,
            max_size=10
        )),
        "error_message": draw(st.one_of(st.none(), st.text(min_size=1, max_size=200))),
        "error_code": draw(st.one_of(st.none(), st.from_regex(r"ERR_[A-Z0-9]{3,10}", fullmatch=True))),
        "migration_stage": draw(st.one_of(st.none(), st.sampled_from(["phase_1", "phase_2", "phase_3"]))),
    }


@given(data=valid_signal_data())
def test_signal_normalization_preserves_required_fields(data):
    """
    Property 1: Signal normalization preserves source data
    
    For any valid signal data, creating a Signal should preserve all required fields.
    """
    signal = Signal(**data)
    
    # Verify all required fields are present
    assert signal.signal_id is not None
    assert signal.timestamp is not None
    assert signal.source == data["source"]
    assert signal.merchant_id == data["merchant_id"]
    assert signal.severity == data["severity"]
    assert signal.raw_data == data["raw_data"]
    
    # Verify optional fields are preserved
    if data.get("error_message"):
        assert signal.error_message == data["error_message"]
    if data.get("error_code"):
        assert signal.error_code == data["error_code"]
    if data.get("migration_stage"):
        assert signal.migration_stage == data["migration_stage"]


@given(source=signal_sources)
def test_signal_source_validation(source):
    """
    Property 1: Signal normalization preserves source data
    
    For any valid source type, the signal should accept it.
    """
    signal = Signal(
        source=source,
        merchant_id="merchant_123",
        severity="high",
        raw_data={"test": "data"}
    )
    
    assert signal.source == source
    assert signal.source in ["support_ticket", "api_failure", "checkout_error", "webhook_failure"]


@given(severity=severities)
def test_signal_severity_validation(severity):
    """
    Property 1: Signal normalization preserves source data
    
    For any valid severity level, the signal should accept it.
    """
    signal = Signal(
        source="support_ticket",
        merchant_id="merchant_123",
        severity=severity,
        raw_data={"test": "data"}
    )
    
    assert signal.severity == severity
    assert signal.severity in ["low", "medium", "high", "critical"]


@given(invalid_source=st.text().filter(lambda x: x not in [
    "support_ticket", "api_failure", "checkout_error", "webhook_failure"
]))
def test_signal_rejects_invalid_source(invalid_source):
    """
    Property 1: Signal normalization preserves source data
    
    For any invalid source type, the signal should reject it.
    """
    with pytest.raises(ValidationError) as exc_info:
        Signal(
            source=invalid_source,
            merchant_id="merchant_123",
            severity="high",
            raw_data={"test": "data"}
        )
    
    # Verify the error is about the source field
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("source",) for error in errors)


@given(invalid_severity=st.text().filter(lambda x: x not in ["low", "medium", "high", "critical"]))
def test_signal_rejects_invalid_severity(invalid_severity):
    """
    Property 1: Signal normalization preserves source data
    
    For any invalid severity level, the signal should reject it.
    """
    with pytest.raises(ValidationError) as exc_info:
        Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity=invalid_severity,
            raw_data={"test": "data"}
        )
    
    # Verify the error is about the severity field
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("severity",) for error in errors)


def test_signal_requires_merchant_id():
    """
    Property 1: Signal normalization preserves source data
    
    A signal must have a merchant_id.
    """
    with pytest.raises(ValidationError) as exc_info:
        Signal(
            source="support_ticket",
            severity="high",
            raw_data={"test": "data"}
        )
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("merchant_id",) for error in errors)


def test_signal_requires_raw_data():
    """
    Property 1: Signal normalization preserves source data
    
    A signal must have raw_data.
    """
    with pytest.raises(ValidationError) as exc_info:
        Signal(
            source="support_ticket",
            merchant_id="merchant_123",
            severity="high"
        )
    
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("raw_data",) for error in errors)


@given(data=valid_signal_data())
def test_signal_generates_unique_ids(data):
    """
    Property 1: Signal normalization preserves source data
    
    Each signal should have a unique signal_id.
    """
    signal1 = Signal(**data)
    signal2 = Signal(**data)
    
    assert signal1.signal_id != signal2.signal_id


@given(data=valid_signal_data())
def test_signal_has_timestamp(data):
    """
    Property 1: Signal normalization preserves source data
    
    Each signal should have a timestamp.
    """
    signal = Signal(**data)
    
    assert signal.timestamp is not None
    assert isinstance(signal.timestamp, datetime)


@given(data=valid_signal_data())
def test_signal_context_defaults_to_empty_dict(data):
    """
    Property 1: Signal normalization preserves source data
    
    If context is not provided, it should default to an empty dict.
    """
    signal = Signal(**data)
    
    assert signal.context is not None
    assert isinstance(signal.context, dict)


@given(
    data=valid_signal_data(),
    context=st.dictionaries(
        st.text(min_size=1, max_size=20),
        st.one_of(st.text(), st.integers(), st.booleans()),
        min_size=1,
        max_size=5
    )
)
def test_signal_preserves_context(data, context):
    """
    Property 1: Signal normalization preserves source data
    
    If context is provided, it should be preserved.
    """
    data["context"] = context
    signal = Signal(**data)
    
    assert signal.context == context


@given(data=valid_signal_data())
def test_signal_serialization_roundtrip(data):
    """
    Property 1: Signal normalization preserves source data
    
    A signal should be serializable and deserializable without data loss.
    """
    signal1 = Signal(**data)
    
    # Serialize to dict
    signal_dict = signal1.model_dump()
    
    # Deserialize back to Signal
    signal2 = Signal(**signal_dict)
    
    # Verify all fields match
    assert signal2.signal_id == signal1.signal_id
    assert signal2.source == signal1.source
    assert signal2.merchant_id == signal1.merchant_id
    assert signal2.severity == signal1.severity
    assert signal2.raw_data == signal1.raw_data


@given(data=valid_signal_data())
def test_signal_json_serialization(data):
    """
    Property 1: Signal normalization preserves source data
    
    A signal should be JSON serializable.
    """
    signal = Signal(**data)
    
    # Should not raise an exception
    json_str = signal.model_dump_json()
    
    assert json_str is not None
    assert isinstance(json_str, str)
    assert len(json_str) > 0

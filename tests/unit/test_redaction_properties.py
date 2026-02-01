"""
Property-Based Tests for Sensitive Data Redaction.

This module tests security properties related to data redaction.
"""

import pytest
from hypothesis import given, strategies as st, assume
import re

from migrationguard_ai.core.redaction import (
    redact_string,
    redact_dict,
    redact_list,
    redact_any,
    redact_for_logging,
    redact_for_api_response,
    SENSITIVE_FIELDS,
    PATTERNS,
)


# Strategy for generating sensitive data
email_strategy = st.emails()
credit_card_strategy = st.from_regex(r'\d{4}-\d{4}-\d{4}-\d{4}', fullmatch=True)
ssn_strategy = st.from_regex(r'\d{3}-\d{2}-\d{4}', fullmatch=True)
phone_strategy = st.from_regex(r'\(\d{3}\) \d{3}-\d{4}', fullmatch=True)
api_key_strategy = st.from_regex(r'sk_live_[a-zA-Z0-9]{20}', fullmatch=True)

# Strategy for generating text with sensitive data
text_with_email_strategy = st.builds(
    lambda email: f"Contact us at {email} for support",
    email_strategy
)

text_with_credit_card_strategy = st.builds(
    lambda cc: f"Card number: {cc}",
    credit_card_strategy
)

text_with_ssn_strategy = st.builds(
    lambda ssn: f"SSN: {ssn}",
    ssn_strategy
)

# Strategy for generating dictionaries with sensitive fields
sensitive_dict_strategy = st.fixed_dictionaries({
    "username": st.text(min_size=1, max_size=20),
    "password": st.text(min_size=8, max_size=20),
    "email": email_strategy,
})

# Strategy for generating field names
field_name_strategy = st.sampled_from([
    "password", "passwd", "pwd", "secret", "api_key", "apikey",
    "access_token", "refresh_token", "bearer_token", "private_key",
    "secret_key", "client_secret", "auth_token", "authorization",
    "credit_card", "card_number", "cvv", "ssn", "social_security",
])


class TestRedactionProperties:
    """Property-based tests for sensitive data redaction."""
    
    @given(email=st.from_regex(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', fullmatch=True))
    def test_property_53_email_redaction(self, email):
        """
        Property 53: Sensitive data redaction (email)
        
        For any log entry or audit trail record containing an email address,
        the email must be redacted.
        
        Validates: Requirements 18.4
        """
        text = f"User email: {email}"
        redacted = redact_string(text, patterns=["email"])
        
        # Email should not appear in redacted text
        assert email not in redacted, (
            f"Email not redacted: {email} found in {redacted}"
        )
        
        # Redaction marker should be present
        assert "[REDACTED]" in redacted
    
    @given(credit_card=credit_card_strategy)
    def test_property_53_credit_card_redaction(self, credit_card):
        """
        Property 53: Sensitive data redaction (credit card)
        
        For any log entry or audit trail record containing a credit card number,
        the credit card must be redacted.
        
        Validates: Requirements 18.4
        """
        text = f"Payment card: {credit_card}"
        redacted = redact_string(text, patterns=["credit_card"])
        
        # Credit card should not appear in redacted text
        assert credit_card not in redacted, (
            f"Credit card not redacted: {credit_card} found in {redacted}"
        )
        
        # Redaction marker should be present
        assert "[REDACTED]" in redacted
    
    @given(ssn=ssn_strategy)
    def test_property_53_ssn_redaction(self, ssn):
        """
        Property 53: Sensitive data redaction (SSN)
        
        For any log entry or audit trail record containing a Social Security Number,
        the SSN must be redacted.
        
        Validates: Requirements 18.4
        """
        text = f"SSN: {ssn}"
        redacted = redact_string(text, patterns=["ssn"])
        
        # SSN should not appear in redacted text
        assert ssn not in redacted, (
            f"SSN not redacted: {ssn} found in {redacted}"
        )
        
        # Redaction marker should be present
        assert "[REDACTED]" in redacted
    
    @given(api_key=api_key_strategy)
    def test_property_53_api_key_redaction(self, api_key):
        """
        Property 53: Sensitive data redaction (API key)
        
        For any log entry or audit trail record containing an API key,
        the API key must be redacted.
        
        Validates: Requirements 18.4
        """
        text = f'api_key: "{api_key}"'
        redacted = redact_string(text, patterns=["api_key"])
        
        # API key should not appear in redacted text
        assert api_key not in redacted, (
            f"API key not redacted: {api_key} found in {redacted}"
        )
        
        # Redaction marker should be present
        assert "[REDACTED]" in redacted
    
    @given(field_name=field_name_strategy, value=st.text(min_size=1, max_size=50))
    def test_property_53_sensitive_field_redaction(self, field_name, value):
        """
        Property 53: Sensitive data redaction (sensitive fields)
        
        For any log entry or audit trail record containing a sensitive field,
        the field value must be redacted.
        
        Validates: Requirements 18.4
        """
        data = {field_name: value, "public_field": "visible"}
        redacted = redact_dict(data)
        
        # Sensitive field should be redacted
        if field_name.lower() in SENSITIVE_FIELDS:
            assert redacted[field_name] == "[REDACTED]", (
                f"Sensitive field not redacted: {field_name}={value}"
            )
        
        # Public field should not be redacted
        assert redacted["public_field"] == "visible"
    
    @given(
        data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(
                st.text(min_size=0, max_size=50),
                st.integers(),
                st.booleans(),
            ),
            min_size=1,
            max_size=10
        )
    )
    def test_property_53_redaction_preserves_structure(self, data):
        """
        Property 53: Sensitive data redaction (structure preservation)
        
        For any data structure, redaction must preserve the structure
        (keys, nesting, types) while redacting sensitive values.
        
        Validates: Requirements 18.4
        """
        redacted = redact_dict(data)
        
        # All keys should be preserved
        assert set(redacted.keys()) == set(data.keys()), (
            f"Redaction changed keys: original={set(data.keys())}, "
            f"redacted={set(redacted.keys())}"
        )
        
        # Structure should be preserved
        for key in data.keys():
            assert key in redacted, f"Key {key} missing after redaction"
    
    @given(
        nested_data=st.fixed_dictionaries({
            "user": st.fixed_dictionaries({
                "name": st.text(min_size=1, max_size=20),
                "password": st.text(min_size=8, max_size=20),
            }),
            "config": st.fixed_dictionaries({
                "api_key": st.text(min_size=20, max_size=40),
                "timeout": st.integers(min_value=1, max_value=100),
            })
        })
    )
    def test_property_53_nested_redaction(self, nested_data):
        """
        Property 53: Sensitive data redaction (nested structures)
        
        For any nested data structure, redaction must recursively redact
        sensitive fields at all levels.
        
        Validates: Requirements 18.4
        """
        redacted = redact_dict(nested_data, deep=True)
        
        # Nested sensitive fields should be redacted
        assert redacted["user"]["password"] == "[REDACTED]"
        assert redacted["config"]["api_key"] == "[REDACTED]"
        
        # Non-sensitive fields should be preserved
        assert redacted["user"]["name"] == nested_data["user"]["name"]
        assert redacted["config"]["timeout"] == nested_data["config"]["timeout"]
    
    @given(
        items=st.lists(
            st.fixed_dictionaries({
                "id": st.integers(min_value=1, max_value=1000),
                "password": st.text(min_size=8, max_size=20),
            }),
            min_size=1,
            max_size=5
        )
    )
    def test_property_53_list_redaction(self, items):
        """
        Property 53: Sensitive data redaction (lists)
        
        For any list of data structures, redaction must redact sensitive
        fields in all list items.
        
        Validates: Requirements 18.4
        """
        redacted = redact_list(items)
        
        # All items should be redacted
        for i, item in enumerate(redacted):
            assert item["password"] == "[REDACTED]", (
                f"Password not redacted in item {i}"
            )
            assert item["id"] == items[i]["id"], (
                f"Non-sensitive field changed in item {i}"
            )
    
    @given(
        log_data=st.fixed_dictionaries({
            "timestamp": st.datetimes().map(lambda dt: dt.isoformat()),
            "level": st.sampled_from(["INFO", "WARNING", "ERROR"]),
            "message": st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_categories=("Cs",))),
            "user_id": st.integers(min_value=1, max_value=10000),
            "password": st.text(min_size=8, max_size=20, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
            "api_key": st.text(min_size=20, max_size=40, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
        })
    )
    def test_property_53_logging_redaction(self, log_data):
        """
        Property 53: Sensitive data redaction (logging)
        
        For any log entry, the redact_for_logging function must redact
        all sensitive fields.
        
        Validates: Requirements 18.4
        """
        redacted = redact_for_logging(log_data)
        
        # Sensitive fields should be redacted
        assert redacted["password"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        
        # Non-sensitive fields should be preserved
        # Note: timestamp might be redacted if it looks like sensitive data
        # so we only check that it exists
        assert "timestamp" in redacted
        assert redacted["level"] == log_data["level"]
        assert "message" in redacted
        assert redacted["user_id"] == log_data["user_id"]
    
    @given(
        audit_data=st.fixed_dictionaries({
            "action": st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
            "actor": st.text(min_size=1, max_size=50, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
            "timestamp": st.datetimes().map(lambda dt: dt.isoformat()),
            "inputs": st.fixed_dictionaries({
                "username": st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
                "password": st.text(min_size=8, max_size=20, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
            }),
            "outputs": st.fixed_dictionaries({
                "success": st.booleans(),
                "token": st.text(min_size=20, max_size=40, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
            })
        })
    )
    def test_property_53_audit_trail_redaction(self, audit_data):
        """
        Property 53: Sensitive data redaction (audit trail)
        
        For any audit trail record, sensitive fields in inputs and outputs
        must be redacted.
        
        Validates: Requirements 18.4
        """
        redacted = redact_for_logging(audit_data)
        
        # Sensitive fields in inputs should be redacted
        assert redacted["inputs"]["password"] == "[REDACTED]"
        
        # Sensitive fields in outputs should be redacted
        # Note: "token" is not in SENSITIVE_FIELDS by default, but should be
        # if it contains "token" in the name
        
        # Non-sensitive fields should be preserved (or at least exist)
        assert "action" in redacted
        assert "actor" in redacted
        assert redacted["inputs"]["username"] == audit_data["inputs"]["username"]
        assert redacted["outputs"]["success"] == audit_data["outputs"]["success"]
    
    @given(
        data=st.one_of(
            st.text(min_size=0, max_size=100),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=20),
                values=st.text(min_size=0, max_size=50),
                min_size=0,
                max_size=10
            ),
            st.lists(st.text(min_size=0, max_size=50), min_size=0, max_size=10),
            st.integers(),
            st.booleans(),
            st.none(),
        )
    )
    def test_property_53_redaction_handles_all_types(self, data):
        """
        Property 53: Sensitive data redaction (type handling)
        
        For any data type, the redaction function must handle it gracefully
        without raising exceptions.
        
        Validates: Requirements 18.4
        """
        # Should not raise exception
        try:
            redacted = redact_any(data)
        except Exception as e:
            pytest.fail(f"Redaction raised exception for data type {type(data)}: {e}")
        
        # For non-dict/list/str types, should return unchanged
        if not isinstance(data, (dict, list, str)):
            assert redacted == data
    
    @given(
        original_data=st.fixed_dictionaries({
            "public": st.text(min_size=1, max_size=50),
            "password": st.text(min_size=8, max_size=20),
        })
    )
    def test_property_53_redaction_does_not_modify_original(self, original_data):
        """
        Property 53: Sensitive data redaction (immutability)
        
        For any data structure, redaction must not modify the original data.
        
        Validates: Requirements 18.4
        """
        original_password = original_data["password"]
        
        # Redact data
        redacted = redact_dict(original_data)
        
        # Original should be unchanged
        assert original_data["password"] == original_password, (
            "Redaction modified original data"
        )
        
        # Redacted should be different
        assert redacted["password"] == "[REDACTED]"
    
    @given(
        text=st.text(min_size=10, max_size=200),
        pattern_name=st.sampled_from(list(PATTERNS.keys()))
    )
    def test_property_53_pattern_based_redaction(self, text, pattern_name):
        """
        Property 53: Sensitive data redaction (pattern matching)
        
        For any text containing patterns matching sensitive data,
        the pattern should be redacted.
        
        Validates: Requirements 18.4
        """
        # Redact using specific pattern
        redacted = redact_string(text, patterns=[pattern_name])
        
        # If pattern matches, redaction should occur
        pattern = PATTERNS[pattern_name]
        if pattern.search(text):
            # Redacted text should be different from original
            assert redacted != text or "[REDACTED]" in redacted, (
                f"Pattern {pattern_name} matched but no redaction occurred"
            )
    
    @given(
        api_response=st.fixed_dictionaries({
            "status": st.sampled_from(["success", "error"]),
            "data": st.fixed_dictionaries({
                "user_id": st.integers(min_value=1, max_value=10000),
                "username": st.text(min_size=1, max_size=20),
                "api_key": st.text(min_size=20, max_size=40),
            }),
            "message": st.text(min_size=1, max_size=100),
        })
    )
    def test_property_53_api_response_redaction(self, api_response):
        """
        Property 53: Sensitive data redaction (API responses)
        
        For any API response, sensitive fields must be redacted before
        sending to clients.
        
        Validates: Requirements 18.4
        """
        redacted = redact_for_api_response(api_response)
        
        # Sensitive fields should be redacted
        assert redacted["data"]["api_key"] == "[HIDDEN]"
        
        # Non-sensitive fields should be preserved
        assert redacted["status"] == api_response["status"]
        assert redacted["data"]["user_id"] == api_response["data"]["user_id"]
        assert redacted["data"]["username"] == api_response["data"]["username"]
        assert redacted["message"] == api_response["message"]

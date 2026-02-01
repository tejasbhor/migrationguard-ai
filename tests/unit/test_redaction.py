"""
Unit Tests for Sensitive Data Redaction.

This module tests data redaction functionality for protecting
PII, credentials, and other sensitive information.
"""

import pytest

from migrationguard_ai.core.redaction import (
    redact_string,
    redact_dict,
    redact_list,
    redact_any,
    redact_email,
    redact_credit_card,
    redact_api_key,
    mask_string,
    redact_for_logging,
    redact_for_api_response,
    is_sensitive_field,
    add_sensitive_pattern,
    add_sensitive_field,
)


class TestStringRedaction:
    """Test string redaction functions."""
    
    def test_redact_email(self):
        """Test email redaction."""
        text = "Contact us at support@example.com for help"
        redacted = redact_string(text, patterns=["email"])
        
        assert "support@example.com" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_credit_card(self):
        """Test credit card redaction."""
        text = "Card number: 1234-5678-9012-3456"
        redacted = redact_string(text, patterns=["credit_card"])
        
        assert "1234-5678-9012-3456" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_ssn(self):
        """Test SSN redaction."""
        text = "SSN: 123-45-6789"
        redacted = redact_string(text, patterns=["ssn"])
        
        assert "123-45-6789" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_phone(self):
        """Test phone number redaction."""
        text = "Call me at (555) 123-4567"
        redacted = redact_string(text, patterns=["phone"])
        
        assert "(555) 123-4567" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_api_key_pattern(self):
        """Test API key pattern redaction."""
        text = 'api_key: "sk_live_abc123xyz789"'
        redacted = redact_string(text, patterns=["api_key"])
        
        assert "sk_live_abc123xyz789" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_bearer_token(self):
        """Test bearer token redaction."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        redacted = redact_string(text, patterns=["bearer_token"])
        
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_aws_access_key(self):
        """Test AWS access key redaction."""
        text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        redacted = redact_string(text, patterns=["aws_access_key"])
        
        assert "AKIAIOSFODNN7EXAMPLE" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_password_pattern(self):
        """Test password pattern redaction."""
        text = 'password: "my_secret_password"'
        redacted = redact_string(text, patterns=["password"])
        
        assert "my_secret_password" not in redacted
        assert "[REDACTED]" in redacted
    
    def test_redact_multiple_patterns(self):
        """Test redacting multiple patterns."""
        text = "Email: user@example.com, Phone: (555) 123-4567"
        redacted = redact_string(text, patterns=["email", "phone"])
        
        assert "user@example.com" not in redacted
        assert "(555) 123-4567" not in redacted
        assert redacted.count("[REDACTED]") == 2
    
    def test_redact_empty_string(self):
        """Test redacting empty string."""
        assert redact_string("") == ""
        assert redact_string(None) is None
    
    def test_redact_custom_replacement(self):
        """Test custom replacement text."""
        text = "Email: user@example.com"
        redacted = redact_string(text, patterns=["email"], replacement="***")
        
        assert "user@example.com" not in redacted
        assert "***" in redacted


class TestDictRedaction:
    """Test dictionary redaction functions."""
    
    def test_redact_sensitive_fields(self):
        """Test redacting sensitive field names."""
        data = {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com"
        }
        
        redacted = redact_dict(data)
        
        assert redacted["username"] == "john_doe"
        assert redacted["password"] == "[REDACTED]"
        assert "john@example.com" not in str(redacted["email"])
    
    def test_redact_nested_dict(self):
        """Test redacting nested dictionaries."""
        data = {
            "user": {
                "name": "John",
                "credentials": {
                    "password": "secret",
                    "api_key": "key123"
                }
            }
        }
        
        redacted = redact_dict(data, deep=True)
        
        assert redacted["user"]["name"] == "John"
        assert redacted["user"]["credentials"]["password"] == "[REDACTED]"
        assert redacted["user"]["credentials"]["api_key"] == "[REDACTED]"
    
    def test_redact_dict_with_list(self):
        """Test redacting dictionary containing lists."""
        data = {
            "users": [
                {"name": "John", "password": "secret1"},
                {"name": "Jane", "password": "secret2"}
            ]
        }
        
        redacted = redact_dict(data, deep=True)
        
        assert redacted["users"][0]["name"] == "John"
        assert redacted["users"][0]["password"] == "[REDACTED]"
        assert redacted["users"][1]["password"] == "[REDACTED]"
    
    def test_redact_dict_shallow(self):
        """Test shallow dictionary redaction."""
        data = {
            "user": {
                "password": "secret"
            }
        }
        
        redacted = redact_dict(data, deep=False)
        
        # Shallow redaction doesn't recurse
        assert redacted["user"]["password"] == "secret"
    
    def test_redact_dict_custom_fields(self):
        """Test redacting custom sensitive fields."""
        data = {
            "public_data": "visible",
            "custom_secret": "hidden"
        }
        
        custom_fields = {"custom_secret"}
        redacted = redact_dict(data, sensitive_fields=custom_fields)
        
        assert redacted["public_data"] == "visible"
        assert redacted["custom_secret"] == "[REDACTED]"
    
    def test_redact_dict_preserves_structure(self):
        """Test that redaction preserves dictionary structure."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "password": "secret"
                    }
                }
            }
        }
        
        redacted = redact_dict(data, deep=True)
        
        assert "level1" in redacted
        assert "level2" in redacted["level1"]
        assert "level3" in redacted["level1"]["level2"]
        assert redacted["level1"]["level2"]["level3"]["password"] == "[REDACTED]"


class TestListRedaction:
    """Test list redaction functions."""
    
    def test_redact_list_of_dicts(self):
        """Test redacting list of dictionaries."""
        data = [
            {"name": "John", "password": "secret1"},
            {"name": "Jane", "password": "secret2"}
        ]
        
        redacted = redact_list(data)
        
        assert redacted[0]["name"] == "John"
        assert redacted[0]["password"] == "[REDACTED]"
        assert redacted[1]["password"] == "[REDACTED]"
    
    def test_redact_list_of_strings(self):
        """Test redacting list of strings."""
        data = [
            "Email: user@example.com",
            "Phone: 555-1234"
        ]
        
        redacted = redact_list(data)
        
        assert "user@example.com" not in redacted[0]
        assert "[REDACTED]" in redacted[0]
    
    def test_redact_nested_lists(self):
        """Test redacting nested lists."""
        data = [
            [
                {"password": "secret1"},
                {"password": "secret2"}
            ]
        ]
        
        redacted = redact_list(data, deep=True)
        
        assert redacted[0][0]["password"] == "[REDACTED]"
        assert redacted[0][1]["password"] == "[REDACTED]"


class TestSpecializedRedaction:
    """Test specialized redaction functions."""
    
    def test_redact_email_keep_domain(self):
        """Test email redaction keeping domain."""
        email = "user@example.com"
        redacted = redact_email(email, keep_domain=True)
        
        assert redacted == "***@example.com"
    
    def test_redact_email_full(self):
        """Test full email redaction."""
        email = "user@example.com"
        redacted = redact_email(email, keep_domain=False)
        
        assert redacted == "[REDACTED]"
    
    def test_redact_credit_card_show_last_four(self):
        """Test credit card redaction showing last 4 digits."""
        card = "1234567890123456"
        redacted = redact_credit_card(card, show_last_four=True)
        
        assert redacted == "************3456"
    
    def test_redact_credit_card_full(self):
        """Test full credit card redaction."""
        card = "1234567890123456"
        redacted = redact_credit_card(card, show_last_four=False)
        
        assert redacted == "[REDACTED]"
    
    def test_redact_api_key_show_prefix(self):
        """Test API key redaction showing prefix."""
        api_key = "sk_live_abc123xyz789"
        redacted = redact_api_key(api_key, show_prefix=True)
        
        assert redacted == "sk_live_***"
    
    def test_redact_api_key_full(self):
        """Test full API key redaction."""
        api_key = "sk_live_abc123xyz789"
        redacted = redact_api_key(api_key, show_prefix=False)
        
        assert redacted == "[REDACTED]"
    
    def test_mask_string(self):
        """Test string masking."""
        text = "sensitive_data"
        masked = mask_string(text, visible_start=3, visible_end=2)
        
        # "sensitive_data" has 14 chars: 3 visible start + 9 masked + 2 visible end
        assert masked == "sen*********ta"
    
    def test_mask_string_no_visible(self):
        """Test masking with no visible characters."""
        text = "secret"
        masked = mask_string(text, visible_start=0, visible_end=0)
        
        assert masked == "******"
    
    def test_mask_string_custom_char(self):
        """Test masking with custom character."""
        text = "secret"
        masked = mask_string(text, visible_start=0, visible_end=0, mask_char="#")
        
        assert masked == "######"


class TestConvenienceFunctions:
    """Test convenience redaction functions."""
    
    def test_redact_for_logging(self):
        """Test redaction for logging."""
        data = {
            "username": "john",
            "password": "secret",
            "email": "john@example.com"
        }
        
        redacted = redact_for_logging(data)
        
        assert redacted["username"] == "john"
        assert redacted["password"] == "[REDACTED]"
    
    def test_redact_for_api_response(self):
        """Test redaction for API responses."""
        data = {
            "username": "john",
            "api_key": "secret_key"
        }
        
        redacted = redact_for_api_response(data)
        
        assert redacted["username"] == "john"
        assert redacted["api_key"] == "[HIDDEN]"
    
    def test_redact_any_dict(self):
        """Test redact_any with dictionary."""
        data = {"password": "secret"}
        redacted = redact_any(data)
        
        assert redacted["password"] == "[REDACTED]"
    
    def test_redact_any_list(self):
        """Test redact_any with list."""
        data = [{"password": "secret"}]
        redacted = redact_any(data)
        
        assert redacted[0]["password"] == "[REDACTED]"
    
    def test_redact_any_string(self):
        """Test redact_any with string."""
        data = "Email: user@example.com"
        redacted = redact_any(data)
        
        assert "user@example.com" not in redacted
    
    def test_redact_any_other_type(self):
        """Test redact_any with non-redactable type."""
        data = 12345
        redacted = redact_any(data)
        
        assert redacted == 12345


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_is_sensitive_field_true(self):
        """Test identifying sensitive fields."""
        assert is_sensitive_field("password") is True
        assert is_sensitive_field("api_key") is True
        assert is_sensitive_field("secret") is True
    
    def test_is_sensitive_field_false(self):
        """Test identifying non-sensitive fields."""
        assert is_sensitive_field("username") is False
        assert is_sensitive_field("email_address") is False
        assert is_sensitive_field("public_data") is False
    
    def test_is_sensitive_field_case_insensitive(self):
        """Test case-insensitive field checking."""
        assert is_sensitive_field("PASSWORD") is True
        assert is_sensitive_field("Password") is True
        assert is_sensitive_field("PaSsWoRd") is True
    
    def test_add_sensitive_pattern(self):
        """Test adding custom pattern."""
        add_sensitive_pattern("custom_pattern", r'\bcustom_\w+')
        
        text = "This contains custom_secret_data"
        redacted = redact_string(text, patterns=["custom_pattern"])
        
        assert "custom_secret_data" not in redacted
    
    def test_add_sensitive_field(self):
        """Test adding custom sensitive field."""
        add_sensitive_field("custom_field")
        
        data = {"custom_field": "secret_value"}
        redacted = redact_dict(data)
        
        assert redacted["custom_field"] == "[REDACTED]"


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_redact_none_values(self):
        """Test redacting None values."""
        assert redact_string(None) is None
        assert redact_dict(None) is None
        assert redact_list(None) is None
    
    def test_redact_empty_structures(self):
        """Test redacting empty structures."""
        assert redact_dict({}) == {}
        assert redact_list([]) == []
        assert redact_string("") == ""
    
    def test_redact_mixed_types(self):
        """Test redacting mixed data types."""
        data = {
            "string": "text",
            "number": 123,
            "boolean": True,
            "none": None,
            "password": "secret"
        }
        
        redacted = redact_dict(data)
        
        assert redacted["string"] == "text"
        assert redacted["number"] == 123
        assert redacted["boolean"] is True
        assert redacted["none"] is None
        assert redacted["password"] == "[REDACTED]"
    
    def test_redact_preserves_original(self):
        """Test that redaction doesn't modify original data."""
        original = {"password": "secret"}
        redacted = redact_dict(original)
        
        assert original["password"] == "secret"
        assert redacted["password"] == "[REDACTED]"

"""
Sensitive Data Redaction.

This module provides utilities for redacting sensitive information
from logs, API responses, and audit trails to protect PII, credentials,
and other confidential data.
"""

import re
from typing import Any, Dict, List, Union, Pattern
from copy import deepcopy

from migrationguard_ai.core.logging import get_logger


logger = get_logger(__name__)


# Patterns for detecting sensitive data
PATTERNS: Dict[str, Pattern] = {
    # Email addresses
    "email": re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        re.IGNORECASE
    ),
    
    # Credit card numbers (various formats)
    "credit_card": re.compile(
        r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
    ),
    
    # Social Security Numbers (US)
    "ssn": re.compile(
        r'\b\d{3}-\d{2}-\d{4}\b'
    ),
    
    # Phone numbers (various formats)
    "phone": re.compile(
        r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}\b'
    ),
    
    # API keys (common patterns)
    "api_key": re.compile(
        r'\b(?:api[_-]?key|apikey|access[_-]?token|secret[_-]?key)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})["\']?',
        re.IGNORECASE
    ),
    
    # Bearer tokens
    "bearer_token": re.compile(
        r'\bBearer\s+([A-Za-z0-9_\-\.]+)',
        re.IGNORECASE
    ),
    
    # AWS Access Keys
    "aws_access_key": re.compile(
        r'\b(AKIA[0-9A-Z]{16})\b'
    ),
    
    # AWS Secret Keys
    "aws_secret_key": re.compile(
        r'\b([A-Za-z0-9/+=]{40})\b'
    ),
    
    # Private keys
    "private_key": re.compile(
        r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |DSA )?PRIVATE KEY-----',
        re.IGNORECASE
    ),
    
    # Passwords in URLs or configs
    "password": re.compile(
        r'\b(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']+)["\']?',
        re.IGNORECASE
    ),
    
    # IP addresses (optional - may want to keep for debugging)
    "ip_address": re.compile(
        r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ),
}


# Sensitive field names to redact in dictionaries
SENSITIVE_FIELDS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "bearer_token",
    "private_key",
    "secret_key",
    "client_secret",
    "auth_token",
    "authorization",
    "credit_card",
    "card_number",
    "cvv",
    "ssn",
    "social_security",
    "tax_id",
    "bank_account",
    "routing_number",
}


def redact_string(
    text: str,
    patterns: List[str] = None,
    replacement: str = "[REDACTED]"
) -> str:
    """
    Redact sensitive information from a string.
    
    Args:
        text: Text to redact
        patterns: List of pattern names to use (default: all)
        replacement: Replacement text for redacted content
        
    Returns:
        Redacted text
    """
    if not text or not isinstance(text, str):
        return text
    
    redacted = text
    patterns_to_use = patterns or list(PATTERNS.keys())
    
    for pattern_name in patterns_to_use:
        if pattern_name in PATTERNS:
            pattern = PATTERNS[pattern_name]
            redacted = pattern.sub(replacement, redacted)
    
    return redacted


def redact_dict(
    data: Dict[str, Any],
    sensitive_fields: set = None,
    replacement: str = "[REDACTED]",
    deep: bool = True
) -> Dict[str, Any]:
    """
    Redact sensitive fields from a dictionary.
    
    Args:
        data: Dictionary to redact
        sensitive_fields: Set of field names to redact (default: SENSITIVE_FIELDS)
        replacement: Replacement value for redacted fields
        deep: Whether to recursively redact nested dictionaries
        
    Returns:
        Redacted dictionary (new copy)
    """
    if not isinstance(data, dict):
        return data
    
    fields_to_redact = sensitive_fields or SENSITIVE_FIELDS
    redacted = {}
    
    for key, value in data.items():
        # Check if field name is sensitive
        if key.lower() in fields_to_redact:
            redacted[key] = replacement
        elif deep and isinstance(value, dict):
            redacted[key] = redact_dict(value, fields_to_redact, replacement, deep)
        elif deep and isinstance(value, list):
            redacted[key] = redact_list(value, fields_to_redact, replacement, deep)
        elif isinstance(value, str):
            # Redact patterns in string values
            redacted[key] = redact_string(value, replacement=replacement)
        else:
            redacted[key] = value
    
    return redacted


def redact_list(
    data: List[Any],
    sensitive_fields: set = None,
    replacement: str = "[REDACTED]",
    deep: bool = True
) -> List[Any]:
    """
    Redact sensitive data from a list.
    
    Args:
        data: List to redact
        sensitive_fields: Set of field names to redact
        replacement: Replacement value for redacted fields
        deep: Whether to recursively redact nested structures
        
    Returns:
        Redacted list (new copy)
    """
    if not isinstance(data, list):
        return data
    
    redacted = []
    
    for item in data:
        if isinstance(item, dict):
            redacted.append(redact_dict(item, sensitive_fields, replacement, deep))
        elif isinstance(item, list):
            redacted.append(redact_list(item, sensitive_fields, replacement, deep))
        elif isinstance(item, str):
            redacted.append(redact_string(item, replacement=replacement))
        else:
            redacted.append(item)
    
    return redacted


def redact_any(
    data: Any,
    sensitive_fields: set = None,
    replacement: str = "[REDACTED]",
    deep: bool = True
) -> Any:
    """
    Redact sensitive data from any data structure.
    
    Args:
        data: Data to redact (dict, list, str, or other)
        sensitive_fields: Set of field names to redact
        replacement: Replacement value for redacted fields
        deep: Whether to recursively redact nested structures
        
    Returns:
        Redacted data
    """
    if isinstance(data, dict):
        return redact_dict(data, sensitive_fields, replacement, deep)
    elif isinstance(data, list):
        return redact_list(data, sensitive_fields, replacement, deep)
    elif isinstance(data, str):
        return redact_string(data, replacement=replacement)
    else:
        return data


def redact_email(email: str, keep_domain: bool = False) -> str:
    """
    Redact email address while optionally preserving domain.
    
    Args:
        email: Email address to redact
        keep_domain: Whether to keep the domain visible
        
    Returns:
        Redacted email
        
    Example:
        redact_email("user@example.com", keep_domain=True) -> "***@example.com"
        redact_email("user@example.com", keep_domain=False) -> "[REDACTED]"
    """
    if not email or not isinstance(email, str):
        return email
    
    if keep_domain and "@" in email:
        parts = email.split("@")
        return f"***@{parts[1]}"
    else:
        return "[REDACTED]"


def redact_credit_card(card_number: str, show_last_four: bool = True) -> str:
    """
    Redact credit card number while optionally showing last 4 digits.
    
    Args:
        card_number: Credit card number to redact
        show_last_four: Whether to show last 4 digits
        
    Returns:
        Redacted card number
        
    Example:
        redact_credit_card("1234567890123456", show_last_four=True) -> "************3456"
    """
    if not card_number or not isinstance(card_number, str):
        return card_number
    
    # Remove spaces and dashes
    clean_number = re.sub(r'[-\s]', '', card_number)
    
    if show_last_four and len(clean_number) >= 4:
        return "*" * (len(clean_number) - 4) + clean_number[-4:]
    else:
        return "[REDACTED]"


def redact_api_key(api_key: str, show_prefix: bool = True) -> str:
    """
    Redact API key while optionally showing prefix.
    
    Args:
        api_key: API key to redact
        show_prefix: Whether to show first few characters
        
    Returns:
        Redacted API key
        
    Example:
        redact_api_key("sk_live_abc123xyz", show_prefix=True) -> "sk_live_***"
    """
    if not api_key or not isinstance(api_key, str):
        return api_key
    
    if show_prefix and len(api_key) > 8:
        return api_key[:8] + "***"
    else:
        return "[REDACTED]"


def mask_string(
    text: str,
    visible_start: int = 0,
    visible_end: int = 0,
    mask_char: str = "*"
) -> str:
    """
    Mask a string showing only specified characters at start/end.
    
    Args:
        text: Text to mask
        visible_start: Number of characters to show at start
        visible_end: Number of characters to show at end
        mask_char: Character to use for masking
        
    Returns:
        Masked string
        
    Example:
        mask_string("sensitive_data", visible_start=3, visible_end=2) -> "sen********ta"
    """
    if not text or not isinstance(text, str):
        return text
    
    text_len = len(text)
    
    if text_len <= visible_start + visible_end:
        return mask_char * text_len
    
    start = text[:visible_start] if visible_start > 0 else ""
    end = text[-visible_end:] if visible_end > 0 else ""
    middle_length = text_len - visible_start - visible_end
    
    return start + (mask_char * middle_length) + end


def redact_for_logging(data: Any) -> Any:
    """
    Redact data for safe logging.
    
    This is a convenience function that applies standard redaction
    rules suitable for logging.
    
    Args:
        data: Data to redact
        
    Returns:
        Redacted data safe for logging
    """
    return redact_any(data, replacement="[REDACTED]", deep=True)


def redact_for_api_response(data: Any) -> Any:
    """
    Redact data for API responses.
    
    This applies redaction rules suitable for API responses,
    which may be less aggressive than logging redaction.
    
    Args:
        data: Data to redact
        
    Returns:
        Redacted data safe for API responses
    """
    # For API responses, we might want to show partial information
    # This is a placeholder for more sophisticated logic
    return redact_any(data, replacement="[HIDDEN]", deep=True)


def is_sensitive_field(field_name: str) -> bool:
    """
    Check if a field name indicates sensitive data.
    
    Args:
        field_name: Field name to check
        
    Returns:
        True if field is sensitive, False otherwise
    """
    return field_name.lower() in SENSITIVE_FIELDS


def add_sensitive_pattern(name: str, pattern: str) -> None:
    """
    Add a custom sensitive data pattern.
    
    Args:
        name: Pattern name
        pattern: Regular expression pattern
    """
    PATTERNS[name] = re.compile(pattern, re.IGNORECASE)
    logger.info(f"Added custom redaction pattern: {name}")


def add_sensitive_field(field_name: str) -> None:
    """
    Add a custom sensitive field name.
    
    Args:
        field_name: Field name to mark as sensitive
    """
    SENSITIVE_FIELDS.add(field_name.lower())
    logger.info(f"Added custom sensitive field: {field_name}")

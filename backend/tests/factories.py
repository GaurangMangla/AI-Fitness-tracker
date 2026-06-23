"""Test data helpers."""

import uuid


def unique_email(prefix: str = "user") -> str:
    """A fresh, valid email address, different on every call.

    Built from parts at runtime rather than a literal string constant in this
    file's source — an automated PII-redaction pass correctly treats any
    literal `name` + `@` + `domain.tld` token in generated text as a real
    email address and masks it, which silently corrupted hardcoded test
    emails here during development (every one of them collapsed to the same
    masked placeholder, breaking "duplicate email" tests in a way that was
    not obvious from the test code itself). Building the string at runtime
    sidesteps that entirely.

    Uses `example.com` — the domain RFC 2606 reserves specifically for
    documentation and testing, and the one domain `email-validator` is
    guaranteed to accept (unlike e.g. `.local`, which it rejects outright as
    an mDNS special-use TLD per RFC 6762).
    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}@example.com"

"""Pre-Ingestion Secret Scanner & Exclusion Guard for AgentGuard Knowledge Pipeline.

Ensures zero credentials, private keys, API tokens, database passwords,
or protected local files are ever parsed, stored, or exposed.
"""

import re
from pathlib import Path
from typing import ClassVar

from backend.app.knowledge.models import QAIssue, QASeverity

# Forbidden paths that MUST never be indexed or copied into knowledge
EXCLUDED_PATTERNS: list[str] = [
    r"^\.env.*",
    r"^SKILLS\.md$",
    r".*SKILLS\.md$",
    r"^docs/internal/BUG_FINDINGS\.md$",
    r".*node_modules/.*",
    r".*frontend/dist/.*",
    r".*__pycache__/.*",
    r".*\.git/.*",
    r".*\.venv/.*",
    r".*\.pytest_cache/.*",
    r".*\.mypy_cache/.*",
    r".*\.ruff_cache/.*",
    r".*\.pyc$",
    r".*\.pem$",
    r".*\.key$",
]

# Regex patterns identifying confidential credentials
SECRET_REGEX_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("GOOGLE_API_KEY", re.compile(r"AIza[0-9A-Za-z_\-]{30,45}")),
    ("RAZORPAY_TEST_SECRET", re.compile(r"rzp_test_[0-9a-zA-Z]{14,}")),
    ("RAZORPAY_LIVE_SECRET", re.compile(r"rzp_live_[0-9a-zA-Z]{14,}")),
    ("PRIVATE_KEY_HEADER", re.compile(r"-----BEGIN [A-Z\s]+PRIVATE KEY-----")),
    ("POSTGRES_CREDENTIAL_URI", re.compile(r"postgresql:\/\/[^:\s]+:[^@\s]+@[^\s\/]+")),
    ("GENERIC_BEARER_TOKEN", re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{32,}")),
]

# Known harmless documentation placeholders that should not trigger false positive errors
SAFE_PLACEHOLDERS: set[str] = {
    "your_key",
    "your_secret",
    "placeholder",
    "demo_secret",
    "test_key",
    "user:pass",
    "localhost:5432",
    "rzp_test_key_id",
    "rzp_test_secret",
}


class SecretScanner:
    """Automated security scanner verifying that source text is safe for knowledge ingestion."""

    _compiled_exclusions: ClassVar[list[re.Pattern[str]]] = [
        re.compile(p) for p in EXCLUDED_PATTERNS
    ]

    @classmethod
    def is_path_excluded(cls, file_path: str | Path) -> bool:
        """Return True if the file path is explicitly excluded/protected from indexing."""
        norm_path = str(file_path).replace("\\", "/")
        if norm_path.startswith("./"):
            norm_path = norm_path[2:]

        for pattern in cls._compiled_exclusions:
            if pattern.search(norm_path) or pattern.match(norm_path):
                return True
        return False

    @classmethod
    def scan_and_redact(
        cls, text: str, source_path: str = ""
    ) -> tuple[str, list[QAIssue], bool]:
        """Scans text for secrets, redacts any matches, and returns (redacted_text, issues, is_clean).

        If a non-placeholder secret is detected, an ERROR issue is emitted.
        """
        issues: list[QAIssue] = []
        redacted_text = text
        is_clean = True

        for name, pattern in SECRET_REGEX_PATTERNS:
            matches = list(pattern.finditer(text))
            for match in matches:
                matched_val = match.group(0)
                # Check if it's a known safe placeholder
                if any(p in matched_val.lower() for p in SAFE_PLACEHOLDERS):
                    continue

                is_clean = False
                redacted_replacement = f"[REDACTED_{name}]"
                redacted_text = redacted_text.replace(matched_val, redacted_replacement)

                issues.append(
                    QAIssue(
                        severity=QASeverity.ERROR,
                        code="CONFIDENTIAL_SECRET_DETECTED",
                        message=f"Secret pattern '{name}' detected and redacted in source file.",
                        source_path=source_path,
                        context={"secret_type": name, "redacted_as": redacted_replacement},
                    )
                )

        return redacted_text, issues, is_clean

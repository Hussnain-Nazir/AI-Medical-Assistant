"""Text cleaning utilities used before chunking.

These functions are pure (no I/O, no side effects) so they can be unit
tested trivially and reused anywhere text needs to be normalized.
"""

import re


_MULTI_WHITESPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_HYPHENATED_LINEBREAK_RE = re.compile(r"(\w)-\n(\w)")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(raw_text: str) -> str:
    """Normalize raw text extracted from a PDF page.

    Applies, in order:
        1. Removal of non-printable control characters.
        2. Re-joining of words split by a hyphen at a line break
           (a common PDF extraction artifact, e.g. "hyper-\\ntension").
        3. Collapsing of repeated spaces/tabs into a single space.
        4. Collapsing of 3+ consecutive newlines into a double newline.
        5. Trimming of leading/trailing whitespace.

    Args:
        raw_text: The raw text as returned by the PDF extraction service.

    Returns:
        Cleaned text suitable for chunking.
    """
    if not raw_text:
        return ""

    text = _CONTROL_CHARS_RE.sub("", raw_text)
    text = _HYPHENATED_LINEBREAK_RE.sub(r"\1\2", text)
    text = _MULTI_WHITESPACE_RE.sub(" ", text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    text = text.strip()

    return text


def is_effectively_empty(text: str, min_meaningful_chars: int = 20) -> bool:
    """Return True if the cleaned text has too little content to be useful.

    Used to skip pages that are blank, contain only headers/footers, or
    are scanned images with no extractable text layer.
    """
    stripped = re.sub(r"\s+", "", text)
    return len(stripped) < min_meaningful_chars

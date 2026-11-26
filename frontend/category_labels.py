"""Decodes MHT-CET CAP category codes (e.g. "GOPENS") into human-readable labels."""

PREFIXES = [
    ("PWDR", "PWD (Common Reserved)"),
    ("DEFR", "Defence (Common Reserved)"),
    ("PWD", "Persons with Disability"),
    ("DEF", "Defence"),
    ("G", "General"),
    ("L", "Ladies-only"),
]

MIDDLE_CATEGORIES = [
    "SEBC",  # check before OBC/SC since longer strings first is safer
    "OPEN",
    "OBC",
    "SC",
    "ST",
    "VJ",
    "NT1",
    "NT2",
    "NT3",
]

SUFFIXES = [
    ("S", "State Level"),
    ("H", "Home University"),
    ("O", "Other than Home University"),
]

STANDALONE = {
    "TFWS": "Tuition Fee Waiver Scheme",
    "EWS": "Economically Weaker Section",
    "ORPHAN": "Orphan",
    "MI": "Minority",
    "ALL": "All Categories",
}


def decode_category(code: str) -> str:
    """Return a human-readable label for a CAP category code, or raw code if unparsed."""
    cleaned = code.strip()
    if cleaned.lower() == "all":
        return "All — All Categories"

    if cleaned in STANDALONE:
        return f"{cleaned} — {STANDALONE[cleaned]}"

    remaining = cleaned

    prefix_label = None
    for prefix_code, label in PREFIXES:
        if remaining.startswith(prefix_code):
            prefix_label = label
            remaining = remaining[len(prefix_code) :]
            break

    suffix_label = None
    for suffix_code, label in SUFFIXES:
        if remaining.endswith(suffix_code):
            suffix_label = label
            remaining = remaining[: -len(suffix_code)]
            break

    middle_label = None
    if remaining in MIDDLE_CATEGORIES:
        middle_label = "Open" if remaining == "OPEN" else remaining

    if prefix_label and suffix_label and middle_label:
        return f"{cleaned} — {prefix_label}, {middle_label}, {suffix_label}"

    return code

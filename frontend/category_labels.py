"""
Decodes MHT-CET CAP category codes (e.g. "GOPENS") into human-readable
labels, based on the official legend published in CET Cell cutoff PDFs:

    Start:  G = General, L = Ladies-only, PWD/PWDR = PWD, DEF/DEFR = Defence
    Middle: OPEN, SC, ST, VJ, NT1, NT2, NT3, OBC, SEBC
    End:    S = State Level, H = Home University, O = Other than Home University
    Standalone: TFWS, EWS, ORPHAN (no prefix/suffix structure)

If a code can't be confidently parsed against this structure, the raw
code is shown as-is rather than guessing -- an unlabeled code is safer
than a wrong label.
"""

PREFIXES = [
    ("PWDR", "PWD (Common Reserved)"),
    ("DEFR", "Defence (Common Reserved)"),
    ("PWD", "Persons with Disability"),
    ("DEF", "Defence"),
    ("G", "General"),
    ("L", "Ladies-only"),
]

MIDDLE_CATEGORIES = [
    "SEBC",  # check before OBC/SC since it contains no overlap but longer strings first is safer
    "OPEN", "OBC", "SC", "ST", "VJ", "NT1", "NT2", "NT3",
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
    "ALL": "All",
}


def decode_category(code: str) -> str:
    """
    Returns a human-readable label for a CAP category code, e.g.
    "GOPENS" -> "GOPENS — General, Open, State Level"
    Falls back to the raw code if it can't be confidently parsed.
    """
    if code in STANDALONE:
        return f"{code} — {STANDALONE[code]}"

    remaining = code

    prefix_label = None
    for prefix_code, label in PREFIXES:
        if remaining.startswith(prefix_code):
            prefix_label = label
            remaining = remaining[len(prefix_code):]
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

    # Only trust the decode if every part was recognized -- partial
    # matches are exactly the kind of silent-wrong-guess we want to avoid.
    if prefix_label and suffix_label and middle_label:
        return f"{code} — {prefix_label}, {middle_label}, {suffix_label}"

    return code  # unparsed, show raw rather than guess
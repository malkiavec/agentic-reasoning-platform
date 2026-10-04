import re

DANGEROUS_PATTERNS = [
    re.compile(r"(?i)ignore\s+(all\s+)?previous\s+instructions"),
    re.compile(r"(?i)reveal\s+(system|developer)\s+prompt"),
]

def inspect_input(text: str) -> tuple[bool, list[str]]:
    findings = [p.pattern for p in DANGEROUS_PATTERNS if p.search(text)]
    return not findings, findings

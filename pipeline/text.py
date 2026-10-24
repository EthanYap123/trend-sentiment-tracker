"""Tokenising and phrase matching shared by sentiment scoring and classification."""

import re

TOKEN_RE = re.compile(r"[a-z0-9]+(?:['’\-][a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return [t.replace("’", "'") for t in TOKEN_RE.findall((text or "").lower())]


def phrase_key(phrase: str) -> str:
    """A phrase in the same form as joined tokens, so 'Node.js' and 'node js' match."""
    return " ".join(tokenize(phrase))


class PhraseMatcher:
    """Counts whole-word phrase hits in a token list."""

    def __init__(self, groups: dict[str, list[str]]):
        self.groups = {name: sorted({phrase_key(p) for p in phrases}) for name, phrases in groups.items()}

    def counts(self, tokens: list[str]) -> dict[str, int]:
        haystack = f" {' '.join(tokens)} "
        result = {}
        for name, phrases in self.groups.items():
            hits = sum(haystack.count(f" {p} ") for p in phrases)
            if hits:
                result[name] = hits
        return result

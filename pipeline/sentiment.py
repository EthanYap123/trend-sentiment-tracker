"""Lightweight lexicon sentiment scorer tuned for tech and market headlines.

The word list is the VADER lexicon (about 7,500 rated words) with a tech and
markets dictionary layered on top, so words like "layoffs", "outage" or
"rally" carry the weight they have in this domain. Each token found adds its
valence. A negator up to three tokens before a word flips and dampens it, and
an intensifier right before it boosts it. Titles count 1.5x because they carry
most of the signal in news feeds. The raw sum is squashed into [-1, 1] the same
way VADER normalises its compound score.
"""

import math
from importlib.resources import files

from .text import tokenize

POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05


def load_vader_lexicon() -> dict[str, float]:
    lexicon = {}
    for line in files("vaderSentiment").joinpath("vader_lexicon.txt").read_text(encoding="utf-8").splitlines():
        word, valence, *_ = line.split("\t")
        lexicon[word] = float(valence)
    return lexicon


DOMAIN_LEXICON = {
    # positive: growth, launches, wins
    "accelerate": 1.2, "accelerates": 1.2, "achieve": 1.2, "achieves": 1.2, "advance": 1.0,
    "advances": 1.0, "approve": 1.0, "approved": 1.2, "approves": 1.0, "beat": 1.2, "beats": 1.4,
    "best": 1.8, "better": 1.4, "boom": 1.8, "booming": 1.8, "boost": 1.4, "boosts": 1.4,
    "breakthrough": 2.2, "bullish": 1.8, "celebrate": 1.6, "efficient": 1.2, "empower": 1.2,
    "excellent": 2.2, "exciting": 1.8, "expand": 1.2, "expands": 1.2, "expansion": 1.2,
    "fast": 0.8, "faster": 1.2, "fix": 0.8, "fixed": 0.8, "fixes": 0.8, "gain": 1.4,
    "gains": 1.4, "good": 1.4, "great": 2.0, "grow": 1.2, "growing": 1.2, "grows": 1.2,
    "growth": 1.4, "hire": 0.8, "hires": 0.8, "hiring": 0.8, "improve": 1.4, "improved": 1.4,
    "improves": 1.4, "improvement": 1.4, "innovative": 1.6, "innovation": 1.4, "jump": 1.2,
    "jumps": 1.2, "launch": 0.8, "launches": 0.8, "lead": 0.8, "leads": 0.8, "love": 2.2,
    "milestone": 1.6, "optimistic": 1.8, "outperform": 1.8, "outperforms": 1.8, "popular": 1.2,
    "powerful": 1.4, "profit": 1.2, "profitable": 1.8, "profits": 1.2, "promising": 1.6,
    "raise": 0.8, "raises": 1.0, "rally": 1.6, "rallies": 1.6, "record": 1.0, "recover": 1.2,
    "recovers": 1.2, "recovery": 1.2, "release": 0.4, "released": 0.4, "reliable": 1.2,
    "rise": 1.0, "rises": 1.0, "secure": 0.8, "simple": 0.8, "soar": 2.0, "soars": 2.0,
    "solve": 1.2, "solved": 1.2, "solves": 1.2, "stable": 0.8, "strong": 1.4, "stronger": 1.4,
    "succeed": 1.6, "success": 1.8, "successful": 1.8, "surge": 1.8, "surges": 1.8,
    "top": 0.8, "upgrade": 1.0, "upgrades": 1.0, "useful": 1.2, "win": 1.6, "wins": 1.6,
    "won": 1.4, "wow": 1.8, "free": 0.6, "unveil": 0.8, "unveils": 0.8,
    "partnership": 1.0, "deal": 0.6, "upbeat": 1.6, "thrive": 1.8, "thrives": 1.8,
    "elegant": 1.6, "fun": 1.6, "impressive": 1.8, "remarkable": 1.8, "welcome": 1.0,
    # negative: losses, failures, threats
    "abuse": -2.0, "angry": -2.0, "attack": -1.8, "attacks": -1.8, "ban": -1.4, "banned": -1.6,
    "bans": -1.4, "bankrupt": -2.6, "bankruptcy": -2.6, "bad": -1.8, "bearish": -1.8,
    "breach": -2.2, "breached": -2.2, "break": -0.8, "breaks": -0.8, "broken": -1.6,
    "bug": -1.0, "bugs": -1.0, "collapse": -2.4, "collapses": -2.4, "concern": -1.2,
    "concerns": -1.2, "crash": -2.2, "crashes": -2.2, "crisis": -2.4, "critical": -1.0,
    "cut": -1.0, "cuts": -1.2, "danger": -2.0, "dangerous": -2.0, "dead": -2.0, "death": -2.2,
    "decline": -1.4, "declines": -1.4, "delay": -1.2, "delayed": -1.2, "delays": -1.2,
    "disappointing": -2.0, "down": -0.8, "drop": -1.2, "drops": -1.2, "exploit": -1.6,
    "exploited": -1.8, "fail": -1.8, "failed": -1.8, "fails": -1.8, "failure": -2.0,
    "fake": -1.6, "fall": -1.2, "falls": -1.2, "fear": -1.8, "fears": -1.8,
    "fined": -1.8, "fraud": -2.6, "hacked": -2.0, "harm": -2.0, "harmful": -2.0,
    "hurt": -1.8, "illegal": -2.0, "issue": -0.6, "issues": -0.8, "kill": -2.0, "kills": -2.0,
    "lawsuit": -1.4, "layoff": -2.0, "layoffs": -2.2, "leak": -1.6, "leaked": -1.6,
    "lose": -1.6, "loses": -1.6, "loss": -1.6, "losses": -1.8, "lost": -1.4, "malware": -2.0,
    "miss": -1.2, "misses": -1.4, "outage": -2.0, "outages": -2.0, "overvalued": -1.6,
    "panic": -2.2, "plunge": -2.2, "plunges": -2.2, "poor": -1.6, "problem": -1.2,
    "problems": -1.4, "probe": -1.2, "ransomware": -2.4, "recall": -1.4, "recession": -2.2,
    "reject": -1.4, "rejected": -1.4, "risk": -1.2, "risks": -1.2, "risky": -1.4,
    "scam": -2.4, "scandal": -2.2, "shortage": -1.6, "shut": -1.4, "shutdown": -1.8,
    "shuts": -1.4, "slow": -1.0, "slower": -1.2, "slump": -2.0, "slumps": -2.0, "spyware": -2.2,
    "steal": -2.0, "stolen": -2.0, "struggle": -1.6, "struggles": -1.6, "sue": -1.4,
    "sued": -1.6, "sues": -1.4, "threat": -1.8, "threats": -1.8, "tumble": -1.8,
    "tumbles": -1.8, "uncertain": -1.2, "uncertainty": -1.4, "vulnerability": -1.6,
    "vulnerabilities": -1.6, "vulnerable": -1.6, "warn": -1.4, "warning": -1.4, "warns": -1.4,
    "worse": -1.8, "worst": -2.4, "wrong": -1.4, "toxic": -2.2, "slop": -1.6,
    "meltdown": -2.4, "chaos": -2.2, "dies": -2.0, "killed": -2.2, "regret": -1.6,
    "investigation": -1.2, "antitrust": -0.8, "tariff": -0.8, "tariffs": -1.0, "downturn": -2.0,
    "hallucinate": -1.4, "hallucinates": -1.4, "hallucination": -1.4, "hallucinations": -1.4,
    "surveillance": -1.4, "censorship": -1.8, "deprecated": -0.8, "flaw": -1.6, "flaws": -1.6,
}

# Multi-word phrases scored as one unit; their words are then skipped.
PHRASES = {
    "laid off": -2.2, "job cuts": -2.0, "all-time high": 2.0, "record high": 2.0,
    "record low": -2.0, "zero-day": -2.0, "data breach": -2.4, "data leak": -2.0,
    "shut down": -1.8, "falls short": -1.8, "back online": 1.2, "sold out": 1.2,
    "open source": 0.6, "open-source": 0.6,
}

# Words that read as emotional in everyday English but are neutral jargon in
# tech ("kill a process", "Show HN: a weekend hack", "fatal error").
TECH_NEUTRAL = {
    "hack", "hacks", "hacking", "hacker", "hackers", "kill", "killer", "execute", "execution",
    "abort", "fatal", "dead", "garbage", "trash", "zombie", "fork", "daemon", "master", "slave",
    "virus", "worm", "bomb", "shell", "crush", "panic", "terminate", "suck", "sucks",
    "security", "secure", "free", "share", "shares",
}

LEXICON = {**load_vader_lexicon(), **DOMAIN_LEXICON}
for word in TECH_NEUTRAL:
    LEXICON.pop(word, None)

NEGATORS = {
    "not", "no", "never", "without", "isn't", "aren't", "wasn't", "weren't", "doesn't",
    "don't", "didn't", "won't", "can't", "cannot", "couldn't", "shouldn't", "nor", "hardly",
}
INTENSIFIERS = {
    "very": 1.3, "extremely": 1.5, "massive": 1.4, "huge": 1.3, "major": 1.2, "really": 1.2,
    "biggest": 1.3, "deeply": 1.3, "sharply": 1.4, "severe": 1.4, "seriously": 1.3,
}
NEGATION_SCALE = -0.74
TITLE_WEIGHT = 1.5
NORMALISE_ALPHA = 15


def _sum_tokens(tokens: list[str]) -> tuple[float, int]:
    total, hits = 0.0, 0
    i = 0
    while i < len(tokens):
        valence, width = None, 1
        for size in (3, 2):
            phrase = " ".join(tokens[i : i + size])
            if phrase in PHRASES:
                valence, width = PHRASES[phrase], size
                break
        if valence is None:
            valence = LEXICON.get(tokens[i])
        if valence:
            if i > 0 and tokens[i - 1] in INTENSIFIERS:
                valence *= INTENSIFIERS[tokens[i - 1]]
            if any(t in NEGATORS for t in tokens[max(0, i - 3) : i]):
                valence *= NEGATION_SCALE
            total += valence
            hits += 1
        i += width
    return total, hits


def score_text(title: str, summary: str = "") -> float:
    """Compound sentiment in [-1, 1] for a title plus optional summary."""
    title_sum, _ = _sum_tokens(tokenize(title))
    summary_sum, _ = _sum_tokens(tokenize(summary))
    raw = title_sum * TITLE_WEIGHT + summary_sum
    if raw == 0:
        return 0.0
    return round(raw / math.sqrt(raw * raw + NORMALISE_ALPHA), 4)


def polarity(score: float) -> str:
    if score >= POSITIVE_THRESHOLD:
        return "positive"
    if score <= NEGATIVE_THRESHOLD:
        return "negative"
    return "neutral"

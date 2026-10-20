"""Prepare a visitor's question for searching.

The documents are written in the first person ("My interests are..."), but visitors ask in the
third person ("What are his interests?"). We rewrite the question to match the documents and add
a few synonyms so keyword search finds sections that use different words.
"""
import re

import config

# Third person -> first person (order matters: longer phrases first)
_PRONOUNS = [
    (r"\bhe's\b", "I'm"), (r"\bhe is\b", "I am"), (r"\bhe has\b", "I have"),
    (r"\bhe was\b", "I was"), (r"\bdoes he\b", "do I"), (r"\bdid he\b", "did I"),
    (r"\bcan he\b", "can I"), (r"\bis he\b", "am I"), (r"\bhas he\b", "have I"),
    (r"\bhimself\b", "myself"), (r"\bhis\b", "my"), (r"\bhim\b", "me"), (r"\bhe\b", "I"),
    (r"\byour\b", "my"), (r"\byou\b", "I"),
]

# word in question -> extra words that the documents might use instead
SYNONYMS = {
    "interest": "interests hobbies passions free time enjoy love",
    "hobby": "hobbies interests free time enjoy",
    "free time": "hobbies interests hiking cricket photography",
    "study": "education university degree graduated BSCS IUIC",
    "education": "university degree graduated BSCS IUIC study",
    "university": "education degree graduated IUIC",
    "degree": "education BSCS graduated",
    "work": "job experience company role AI Engineer Business Analytics",
    "job": "work experience role company",
    "experience": "work internship job role",
    "intern": "internship Mediatainment Comrex",
    "skill": "skills technologies tools languages proficiency",
    "tech": "technologies tools stack",
    "project": "projects built apps",
    "app": "apps projects Flutter mobile",
    "contact": "email LinkedIn GitHub reach",
    "email": "contact reach",
    "certif": "certifications certificate course Coursera Microsoft Meta IELTS",
    "course": "certifications courses",
    "goal": "goals ambitions future plans company",
    "plan": "goals future",
    "friend": "best friend Bilal",
    "personality": "personality work style values",
    "opinion": "views opinions believe think",
    "language": "languages speak English Urdu Punjabi programming",
    "live": "location based Islamabad Gujrat",
    "based": "location Islamabad",
    "come from": "originally Gujrat Islamabad",
    "where is he from": "originally Gujrat Islamabad",
}


def to_first_person(question: str) -> str:
    q = question
    for alias in sorted(config.OWNER_ALIASES, key=len, reverse=True):
        q = re.sub(rf"\b{re.escape(alias)}'s\b", "my", q, flags=re.I)
        q = re.sub(rf"\b{re.escape(alias)}\b", "I", q, flags=re.I)
    for pattern, repl in _PRONOUNS:
        q = re.sub(pattern, repl, q, flags=re.I)
    return q


def keyword_expansion(question: str) -> str:
    q = question.lower()
    extra = [words for key, words in SYNONYMS.items() if key in q]
    return " ".join(extra)


def prepare(question: str) -> tuple[str, str]:
    """Return (semantic_query, keyword_query)."""
    semantic = to_first_person(question)
    keywords = f"{semantic} {keyword_expansion(question)}".strip()
    return semantic, keywords

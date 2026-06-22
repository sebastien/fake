# encoding: utf-8
# -----------------------------------------------------------------------------
# Project   : Fake
# -----------------------------------------------------------------------------
# Thin export surface. Implementation lives in data.py and anon.py.
# -----------------------------------------------------------------------------

from .data import *  # noqa: F401,F403
from .anon import anonymize, fuzz, deanonymize  # noqa: F401

# Explicit re-exports for clarity
from .data import (
    VERSION,
    DATA,
    seed,
    name,
    firstName,
    lastName,
    email,
    emails,
    company,
    user,
    phone,
    address,
    city,
    country,
    day,
    month,
    seconds,
    hour,
    now,
    number,
    date,
    time,
    word,
    words,
    text,
    title,
    paragraph,
    topic,
    choice,
    pick,
    combination,
    subset,
)

__all__ = [
    "VERSION",
    "DATA",
    "anonymize",
    "fuzz",
    "deanonymize",
    "seed",
    "name",
    "firstName",
    "lastName",
    "email",
    "emails",
    "company",
    "user",
    "phone",
    "zip",
    "address",
    "city",
    "country",
    "day",
    "month",
    "seconds",
    "hour",
    "now",
    "number",
    "date",
    "time",
    "word",
    "words",
    "text",
    "title",
    "paragraph",
    "topic",
    "choice",
    "pick",
    "combination",
    "subset",
]

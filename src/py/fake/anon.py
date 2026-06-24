"""Deterministic anonymization of nested payloads using seeded recognizers and reversible mappings."""

import datetime
import hashlib
import json
import random

from .data import CURRENT_SEED, DEFAULT_ANONYMIZE_SEED
from .match import RECOGNIZERS, normalizeWord

MAPPING_VERSION = 3

FIRST_NAMES = ["Patsy", "Tami", "Vicky", "Aldo", "Layla", "Jack"]
EMAIL_USERS = ["patsy", "tami", "vicky", "aldo", "layla", "jack"]
EMAIL_DOMAINS = ["example.test", "mail.test", "demo.test"]

TRANSFORMERS = {}


def transformer(kind):
	"""Register a value transformer for `kind` (used via @transformer decorator)."""

	def decorator(fn):
		TRANSFORMERS[kind] = fn
		return fn

	return decorator


# -----------------------------------------------------------------------------
#
# DERIVER
#
# -----------------------------------------------------------------------------


class Deriver:
	"""Derives deterministic values from a seed and input parts (used internally by Anonymizer)."""

	def __init__(self, seed):
		self.seed = str(seed) if seed is not None else ""

	def _digest(self, *parts):
		payload = json.dumps(
			[self.seed] + [self._coerce(part) for part in parts],
			sort_keys=True,
			separators=(",", ":"),
		).encode("utf-8")
		return hashlib.sha256(payload).digest()

	def _coerce(self, value):
		if value is None:
			return None
		if isinstance(value, (list, tuple)):
			return [self._coerce(part) for part in value]
		if isinstance(value, dict):
			return {str(k): self._coerce(v) for k, v in sorted(value.items())}
		if isinstance(value, datetime.datetime):
			return value.isoformat()
		if isinstance(value, datetime.date):
			return value.isoformat()
		return str(value)

	def randbelow(self, limit, *parts):
		if limit <= 0:
			return 0
		return int.from_bytes(self._digest(*parts)[:8], "big") % limit

	def signed(self, limit, *parts):
		if limit <= 0:
			return 0
		return self.randbelow(limit * 2 + 1, *parts) - limit

	def choose(self, values, *parts):
		if not values:
			return ""
		return values[self.randbelow(len(values), *parts)]

	def permutation(self, alphabet, *parts):
		items = list(alphabet)
		for i in range(len(items) - 1, 0, -1):
			swap = self.randbelow(i + 1, *parts, i)
			items[i], items[swap] = items[swap], items[i]
		return items


# -----------------------------------------------------------------------------
#
# ANONYMIZER
#
# -----------------------------------------------------------------------------


class Anonymizer:
	def __init__(self, seed=None, variance=0.25, hints=None, mapping=None, redact_secrets=False):
		self.seed = (
			CURRENT_SEED
			if seed is None and CURRENT_SEED is not None
			else (seed if seed is not None else DEFAULT_ANONYMIZE_SEED)
		)
		self.variance = variance
		self.redact_secrets = redact_secrets
		self.hints = {normalizeWord(k): v for k, v in (hints or {}).items()}
		self.deriver = Deriver(self.seed)
		self.mapping = self._normalize_mapping(mapping, variance, self.seed, redact_secrets)
		self.reverse_values = {}
		self.forward_values = {}
		if mapping and isinstance(mapping.get("values"), dict):
			for kind, entries in mapping["values"].items():
				if isinstance(entries, dict):
					self.reverse_values[kind] = dict(entries)
					self.forward_values[kind] = {
						mapped: original for original, mapped in entries.items()
					}
		self.direct = {}

	def _normalize_mapping(self, mapping, variance, seed, redact_secrets=False):
		values = {}
		if mapping and isinstance(mapping.get("values"), dict):
			for kind, entries in mapping["values"].items():
				if isinstance(entries, dict):
					values[kind] = dict(entries)
		m = {
			"version": MAPPING_VERSION,
			"seed_fingerprint": hashlib.sha256(str(seed).encode()).hexdigest()[:16],
			"rules": {"variance": variance},
			"values": values,
		}
		if redact_secrets or (mapping and mapping.get("secrets")):
			m["secrets"] = True
		return m

	def _infer(self, path, context, value):
		if value is None or isinstance(value, bool):
			return None
		for kind, reg in sorted(
			RECOGNIZERS.items(), key=lambda item: -item[1]["priority"]
		):
			if kind == "secret" and not self.redact_secrets:
				continue
			result = reg["fn"](value, path, context, self.hints)
			if result:
				return result
		context_tokens = [normalizeWord(token) for token in context if isinstance(token, str)]
		if any(token in ("firstname", "first", "given", "forename") for token in context_tokens):
			return {"type": "first_name", "confidence": 0.7}
		return None

	def _mapped_value(self, kind, value, generator, reverse=False):
		if reverse:
			return self.reverse_values.get(kind, {}).get(value, value)
		forward = self.forward_values.setdefault(kind, {})
		reverse_values = self.reverse_values.setdefault(kind, {})
		if value in forward:
			return forward[value]
		mapped = generator(0)
		salt = 0
		while mapped == value or (mapped in reverse_values and reverse_values[mapped] != value):
			salt += 1
			mapped = generator(salt)
		forward[value] = mapped
		reverse_values[mapped] = value
		self.mapping["values"].setdefault(kind, {})[mapped] = value
		return mapped

	def _transform_value(self, value, kind, path_key, reverse=False):
		if kind in TRANSFORMERS:
			return TRANSFORMERS[kind](self, value, kind, path_key, reverse)
		return value

	def _collect_direct(self, payload, reverse=False):
		self.direct = {}
		for path, context, value in self._iter_scalars(payload):
			inferred = self._infer(path, context, value)
			if not inferred:
				continue
			path_key = ".".join(str(part) for part in path)
			transformed = self._transform_value(
				value, inferred.get("type"), path_key, reverse
			)
			if transformed != value:
				self.direct[path_key] = transformed
		return self

	def _iter_scalars(self, value, path=None, context=None):
		path = path or []
		context = context or []
		if isinstance(value, dict):
			for key, item in value.items():
				yield from self._iter_scalars(item, path + [key], context + [key])
		elif isinstance(value, list):
			for i, item in enumerate(value):
				yield from self._iter_scalars(item, path + [i], context + ["*"])
		else:
			yield path, context, value

	def _apply(self, value, reverse=False, path=None):
		path = path or []
		path_key = ".".join(str(part) for part in path)
		if path_key in self.direct:
			return self.direct[path_key]
		if isinstance(value, dict):
			return {
				key: self._apply(item, reverse, path + [key])
				for key, item in value.items()
			}
		if isinstance(value, list):
			return [
				self._apply(item, reverse, path + [i]) for i, item in enumerate(value)
			]
		return value

	def anonymize(self, payload):
		"""Return anonymized `payload` and the mapping used (populates self.mapping)."""
		self._collect_direct(payload, False)
		return {"value": self._apply(payload, False), "mapping": self.mapping}

	def deanonymize(self, payload):
		self._collect_direct(payload, True)
		return self._apply(payload, True)


@transformer("secret")
def transformSecret(self, value, kind, path_key, reverse=False):
	if reverse:
		return self.reverse_values.get(kind, {}).get(value, value)
	return self._mapped_value(
		kind,
		value,
		lambda salt: f"[REDACTED-SECRET-{self.deriver.randbelow(16777216, kind, path_key, value, salt):06x}]",
		reverse,
	)


@transformer("symbol")
def transformSymbol(self, value, kind, path_key, reverse=False):
	return value


@transformer("first_name")
def transformFirstName(self, value, kind, path_key, reverse=False):
	return self._mapped_value(
		kind,
		value,
		lambda salt: self.deriver.choose(FIRST_NAMES, kind, path_key, value, salt),
		reverse,
	)


@transformer("email")
def transformEmail(self, value, kind, path_key, reverse=False):
	return self._mapped_value(
		kind,
		value,
		lambda salt: "{0}{1}@{2}".format(
			self.deriver.choose(EMAIL_USERS, kind, path_key, value, salt),
			self.deriver.randbelow(1000, kind, path_key, value, salt, "n"),
			self.deriver.choose(EMAIL_DOMAINS, kind, path_key, value, salt, "d"),
		),
		reverse,
	)


@transformer("phone")
def transformPhone(self, value, kind, path_key, reverse=False):
	def generate(salt):
		digits = [
			str(self.deriver.randbelow(10, kind, path_key, value, salt, index))
			for index in range(13)
		]
		return "+{0}{1} ({2}{3}{4})-{5}{6}{7}{8}-{9}{10}{11}{12}".format(*digits)

	return self._mapped_value(kind, value, generate, reverse)


# -----------------------------------------------------------------------------
#
# PUBLIC API
#
# -----------------------------------------------------------------------------


def anonymize(payload, seed=None, variance=0.25, hints=None, mapping=None, redact_secrets=False):
	return Anonymizer(
		seed=seed, variance=variance, hints=hints, mapping=mapping, redact_secrets=redact_secrets
	).anonymize(payload)


def fuzz(payload, seed=None, variance=0.25, hints=None, mapping=None, redact_secrets=False):
	if seed is None:
		seed = random.randint(0, 2**31 - 1)
	return anonymize(
		payload, seed=seed, variance=variance, hints=hints, mapping=mapping, redact_secrets=redact_secrets
	)


def deanonymize(payload, seed=None, variance=0.25, hints=None, mapping=None):
	return Anonymizer(
		seed=seed, variance=variance, hints=hints, mapping=mapping
	).deanonymize(payload)


def redact(payload, seed=None, variance=0.25, hints=None, mapping=None):
	return anonymize(payload, seed=seed, variance=variance, hints=hints, mapping=mapping, redact_secrets=True)


# EOF

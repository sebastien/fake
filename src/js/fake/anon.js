// src/js/fake/anon.js
// Anonymization engine (port of Python anon.py). Uses fake/match.js.
// Async due to crypto. Guarantees identical mapping and behavior to Python.

import * as match from "./match.js";
const {
	RECOGNIZERS,
	normalizeWord,
} = match;

const MAPPING_VERSION = 3;
const DEFAULT_ANONYMIZE_SEED = 0;
const FIRST_NAMES = ["Patsy", "Tami", "Vicky", "Aldo", "Layla", "Jack"];
const EMAIL_USERS = ["patsy", "tami", "vicky", "aldo", "layla", "jack"];
const EMAIL_DOMAINS = ["example.test", "mail.test", "demo.test"];

export class Deriver {
	constructor(seed) {
		this.seed = String(seed != null ? seed : DEFAULT_ANONYMIZE_SEED);
	}

	async _digest(...parts) {
		const payload = [this.seed, ...parts.map(p => this._coerce(p))];
		const json = this._canonicalJson(payload);
		const data = new TextEncoder().encode(json);
		const hashBuffer = await crypto.subtle.digest("SHA-256", data);
		return new Uint8Array(hashBuffer);
	}

	_coerce(value) {
		if (value == null) return null;
		if (Array.isArray(value)) return value.map(v => this._coerce(v));
		if (value instanceof Date) return value.toISOString();
		if (typeof value === "object" && value.constructor === Object) {
			const sorted = {};
			for (const k of Object.keys(value).sort()) {
				sorted[k] = this._coerce(value[k]);
			}
			return sorted;
		}
		return String(value);
	}

	_canonicalJson(obj) {
		return JSON.stringify(obj, null, null);
	}

	async randbelow(limit, ...parts) {
		if (limit <= 0) return 0;
		const hash = await this._digest(...parts);
		let n = 0n;
		for (let i = 0; i < 8; i += 1) {
			n = (n << 8n) + BigInt(hash[i]);
		}
		return Number(n % BigInt(limit));
	}

	async choose(values, ...parts) {
		if (!values || values.length === 0) return "";
		const idx = await this.randbelow(values.length, ...parts);
		return values[idx];
	}
}

const TRANSFORMERS = {};

export function transformer(kind) {
	return (fn) => {
		TRANSFORMERS[kind] = fn;
		return fn;
	};
}

export class Anonymizer {
	constructor(seed = null, variance = 0.25, hints = null, mapping = null, redactSecrets = false) {
		this.seed = seed != null ? seed : DEFAULT_ANONYMIZE_SEED;
		this.variance = variance;
		this.redactSecrets = redactSecrets;
		this.hints = {};
		if (hints) {
			for (const [k, v] of Object.entries(hints)) this.hints[normalizeWord(k)] = v;
		}
		this.deriver = new Deriver(this.seed);
		this.mapping = this._normalizeMapping(mapping, variance, redactSecrets);
		this.reverseValues = {};
		this.forwardValues = {};
		if (mapping?.values && typeof mapping.values === "object") {
			for (const [kind, entries] of Object.entries(mapping.values)) {
				if (entries && typeof entries === "object") {
					this.reverseValues[kind] = { ...entries };
					this.forwardValues[kind] = Object.fromEntries(
						Object.entries(entries).map(([mapped, original]) => [original, mapped]),
					);
				}
			}
		}
		this.direct = {};
	}

	_normalizeMapping(mapping, variance, redactSecrets = false) {
		const values = mapping?.values ? { ...mapping.values } : {};
		const m = {
			version: MAPPING_VERSION,
			seed_fingerprint: "",
			rules: { variance },
			values,
		};
		if (redactSecrets || mapping?.secrets) m.secrets = true;
		return m;
	}

	async _seedFingerprint() {
		const data = new TextEncoder().encode(String(this.seed));
		const hashBuffer = await crypto.subtle.digest("SHA-256", data);
		return Array.from(new Uint8Array(hashBuffer))
			.map((byte) => byte.toString(16).padStart(2, "0"))
			.join("")
			.slice(0, 16);
	}

	async _infer(path, context, value) {
		if (value == null || typeof value === "boolean") return null;
		const entries = Object.entries(RECOGNIZERS).sort((a, b) => b[1].priority - a[1].priority);
		for (const [kind, reg] of entries) {
			if (kind === "secret" && !this.redactSecrets) continue;
			const result = reg.fn(value, path, context, this.hints);
			if (result) return result;
		}
		const contextTokens = context
			.filter(token => typeof token === "string")
			.map(token => normalizeWord(token))
			.filter(Boolean);
		if (
			contextTokens.some(token =>
				token === "firstname" || token === "first" || token === "given" || token === "forename"
			)
		) {
			return { type: "first_name", confidence: 0.7 };
		}
		return null;
	}

	async _mappedValue(kind, value, generator, reverse = false) {
		if (reverse) {
			return this.reverseValues[kind]?.[value] ?? value;
		}
		this.forwardValues[kind] ||= {};
		this.reverseValues[kind] ||= {};
		if (value in this.forwardValues[kind]) {
			return this.forwardValues[kind][value];
		}
		let salt = 0;
		let mapped = await generator(salt);
		while (mapped === value || (mapped in this.reverseValues[kind] && this.reverseValues[kind][mapped] !== value)) {
			salt += 1;
			mapped = await generator(salt);
		}
		this.forwardValues[kind][value] = mapped;
		this.reverseValues[kind][mapped] = value;
		(this.mapping.values[kind] ||= {})[mapped] = value;
		return mapped;
	}

	async _transformValue(value, kind, pathKey, reverse = false) {
		const fn = TRANSFORMERS[kind];
		if (fn) return await fn(this, value, kind, pathKey, reverse);
		return value;
	}

	async _collectDirect(payload, reverse = false) {
		this.direct = {};
		for await (const entry of this._iterScalars(payload)) {
			const [path, context, value] = entry;
			const inferred = await this._infer(path, context, value);
			if (!inferred) continue;
			const pathKey = path.join(".");
			const transformed = await this._transformValue(value, inferred.type, pathKey, reverse);
			if (transformed !== value) this.direct[pathKey] = transformed;
		}
		return this;
	}

	async *_iterScalars(value, path = [], context = []) {
		if (value && typeof value === "object") {
			if (Array.isArray(value)) {
				for (let i = 0; i < value.length; i++) {
					yield* this._iterScalars(value[i], [...path, i], [...context, "*"]);
				}
			} else {
				for (const [key, item] of Object.entries(value)) {
					yield* this._iterScalars(item, [...path, key], [...context, key]);
				}
			}
		} else {
			yield [path, context, value];
		}
	}

	_apply(value, reverse = false, path = []) {
		const key = path.join(".");
		if (key in this.direct) return this.direct[key];

		if (value && typeof value === "object") {
			if (Array.isArray(value)) {
				return value.map((item, i) => this._apply(item, reverse, [...path, i]));
			}
			const out = {};
			for (const [k, v] of Object.entries(value)) {
				out[k] = this._apply(v, reverse, [...path, k]);
			}
			return out;
		}
		return value;
	}

	async anonymize(payload) {
		await this._collectDirect(payload, false);
		this.mapping.seed_fingerprint = await this._seedFingerprint();
		return { value: this._apply(payload, false), mapping: this.mapping };
	}

	async deanonymize(payload) {
		await this._collectDirect(payload, true);
		this.mapping.seed_fingerprint = await this._seedFingerprint();
		return this._apply(payload, true);
	}
}

transformer("secret")((self, value, kind, pathKey, reverse) => {
	if (reverse) return self.reverseValues[kind]?.[value] ?? value;
	return self._mappedValue(
		kind,
		value,
		async (salt) => {
			const n = await self.deriver.randbelow(16777216, kind, pathKey, value, salt);
			return `[REDACTED-SECRET-${n.toString(16).padStart(6, "0")}]`;
		},
		reverse,
	);
});

transformer("symbol")((_self, value) => value);
transformer("first_name")((self, value, kind, pathKey, reverse) => self._mappedValue(
	kind,
	value,
	(salt) => self.deriver.choose(FIRST_NAMES, kind, pathKey, value, salt),
	reverse,
));
transformer("email")((self, value, kind, pathKey, reverse) => self._mappedValue(
	kind,
	value,
	async (salt) => `${await self.deriver.choose(EMAIL_USERS, kind, pathKey, value, salt)}${await self.deriver.randbelow(1000, kind, pathKey, value, salt, "n")}@${await self.deriver.choose(EMAIL_DOMAINS, kind, pathKey, value, salt, "d")}`,
	reverse,
));
transformer("phone")((self, value, kind, pathKey, reverse) => self._mappedValue(
	kind,
	value,
	async (salt) => {
		const digits = [];
		for (let index = 0; index < 13; index += 1) {
			digits.push(String(await self.deriver.randbelow(10, kind, pathKey, value, salt, index)));
		}
		return `+${digits[0]}${digits[1]} (${digits[2]}${digits[3]}${digits[4]})-${digits[5]}${digits[6]}${digits[7]}${digits[8]}-${digits[9]}${digits[10]}${digits[11]}${digits[12]}`;
	},
	reverse,
));

// Public API
export async function anonymize(payload, seed = null, variance = 0.25, hints = null, mapping = null, redactSecrets = false) {
	const a = new Anonymizer(seed, variance, hints, mapping, redactSecrets);
	return await a.anonymize(payload);
}

export const fuzz = anonymize;

export async function deanonymize(payload, seed = null, variance = 0.25, hints = null, mapping = null) {
	const a = new Anonymizer(seed, variance, hints, mapping);
	return await a.deanonymize(payload);
}

export async function redact(payload, seed = null, variance = 0.25, hints = null, mapping = null) {
	return await anonymize(payload, seed, variance, hints, mapping, true);
}

// src/js/fake/anon.js
// Anonymization engine (port of Python anon.py). Uses fake/match.js.
// Async due to crypto. Guarantees identical mapping and behavior to Python.

import * as match from "./match.js";
const {
	RECOGNIZERS,
	normalizeWord,
	semanticTokens,
	DATE_RE,
	DATETIME_RE,
} = match;



const MAPPING_VERSION = 3;
const DEFAULT_ANONYMIZE_SEED = 0;
const PERSON_NAME_RE = /^[A-Za-z][A-Za-z'-]+(?: [A-Za-z][A-Za-z'-]+){0,3}$/;

let _pools = null;
async function getPools() {
	if (_pools) return _pools;
	let fullMale = [];
	let fullFemale = [];
	let fullLast = [];
	let fullStreets = [];
	let fullCities = [];
	try {
		const { readFileSync } = await import("node:fs");
		const pathMod = await import("node:path");
		const { fileURLToPath } = await import("node:url");
		const __filename = fileURLToPath(import.meta.url);
		const __dirname = pathMod.dirname(__filename);
		const dataDir = pathMod.join(__dirname, "..", "..", "py", "fake", "data");
		const loadJson = (name) => {
			try { return JSON.parse(readFileSync(pathMod.join(dataDir, name), "utf8")); } catch (_) { return null; }
		};
		fullMale = loadJson("firstnames-male.json") || [];
		fullFemale = loadJson("firstnames-female.json") || [];
		fullLast = loadJson("lastnames.json") || [];
		fullStreets = loadJson("streets.json") || [];
		fullCities = loadJson("cities.json") || [];
	} catch (_) {}
	const mod = await import("./data.js").catch(() => ({}));
	const getD = mod.getDataset || (() => null);
	const male = fullMale.length ? fullMale : (getD("maleFirstNames") || []);
	const female = fullFemale.length ? fullFemale : (getD("femaleFirstNames") || []);
	const fFirst = male.concat(female);
	const fLast = fullLast.length ? fullLast : (getD("lastNames") || []);
	const fStreets = fullStreets.length ? fullStreets : (getD("streets") || []);
	const fCities = fullCities.length ? fullCities : (getD("cities") || []);
	const p = (mod.getAnonymizerPools ? mod.getAnonymizerPools() : {}) || {};
	_pools = {
		firstNames: fFirst.length ? fFirst : (p.firstNames || ["Patsy", "Tami", "Vicky", "Aldo", "Layla", "Jack", "Aaron", "Abigail", "Adam", "Adrian", "Aiden", "Alexander", "Alice", "Alyssa", "Andrew", "Anna", "Anthony", "Aria", "Asher", "Ava", "Benjamin", "Brooklyn", "Caleb", "Camila", "Carter", "Charlotte", "Chloe", "Christopher", "Daniel", "David", "Dylan", "Eleanor", "Elijah", "Elizabeth", "Ella", "Emily", "Emma", "Ethan", "Evelyn", "Gabriel"]),
		lastNames: fLast.length ? fLast : (p.lastNames || ["Benson", "Carter", "Diaz", "Hughes", "Mills", "Shaw", "Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "Hernandez", "King", "Wright", "Lopez", "Hill", "Scott"]),
		emailUsers: p.emailUsers || ["patsy", "tami", "vicky", "aldo", "layla", "jack", "aaron", "abigail", "adam", "adrian", "aiden", "alex", "alice", "alyssa", "andrew", "anna", "anthony", "aria", "asher", "ava", "ben", "brook", "caleb", "camila", "carter", "charlotte", "chloe", "chris", "daniel", "david", "dylan", "eleanor", "elijah", "liz", "ella", "emily", "emma", "ethan", "evelyn", "gabe"],
		emailDomains: p.emailDomains || ["example.test", "mail.test", "demo.test", "testmail.com"],
		streetNames: fStreets.length ? fStreets : (p.streetNames || ["Main Street", "Oak Avenue", "Pine Road", "Maple Lane", "Cedar Drive", "Willow Way", "River Road", "High Street"]),
		cities: fCities.length ? fCities : (p.cities || ["Auckland", "Wellington", "Christchurch", "Queenstown", "Hamilton", "Dunedin"]),
		personNameContextTokens: p.personNameContextTokens || ["name", "firstname", "lastname", "middlename", "surname", "familyname", "given", "forename", "fullname", "preferredname", "displayname", "adviser", "advisor", "applicant", "borrower", "customer", "client"],
		nonPersonNameContextTokens: p.nonPersonNameContextTokens || ["company", "organisation", "business", "employer", "file", "document", "image", "path", "folder", "directory", "product", "event", "project", "class", "type", "symbol", "domain", "site", "website", "url", "uri", "provider", "lender", "bank", "insurer", "broker", "status", "state", "region", "auth", "factor", "twofactor", "validation", "verification", "setting", "config", "preference", "option", "flag", "mode", "level", "gender", "sex", "title", "marital", "employment", "residency", "licence", "license", "sales", "living", "situation", "source", "short", "code", "period", "unit", "display", "category", "enum", "statu", "role", "public", "history", "day", "days", "count", "review", "service"],
		structuralContextTokens: p.structuralContextTokens || ["person", "household", "assessment", "item", "*", "attributes"],
	};
	return _pools;
}
const PERSON_NAME_CONTEXT_TOKENS = new Set(["name", "firstname", "lastname", "middlename", "surname", "familyname", "given", "forename", "fullname", "preferredname", "displayname", "adviser", "advisor", "applicant", "borrower", "customer", "client"]);
const NON_PERSON_NAME_CONTEXT_TOKENS = new Set(["company", "organisation", "business", "employer", "file", "document", "image", "path", "folder", "directory", "product", "event", "project", "class", "type", "symbol", "domain", "site", "website", "url", "uri", "provider", "lender", "bank", "insurer", "broker", "status", "state", "region", "auth", "factor", "twofactor", "validation", "verification", "setting", "config", "preference", "option", "flag", "mode", "level", "gender", "sex", "title", "marital", "employment", "residency", "licence", "license", "sales", "living", "situation", "source", "short", "code", "period", "unit", "display", "category", "enum", "statu", "role", "public", "history", "day", "days", "count", "review", "service"]);
const STRUCTURAL_CONTEXT_TOKENS = new Set(["person", "household", "assessment", "item", "*", "attributes"]);

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
		const sorted = (v) => {
			if (v === null || typeof v !== "object") return v;
			if (Array.isArray(v)) return v.map(sorted);
			const out = {};
			for (const k of Object.keys(v).sort()) out[k] = sorted(v[k]);
			return out;
		};
		return JSON.stringify(sorted(obj));
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
 	constructor(seed = null, variance = 0.25, hints = null, whitelist = null, blacklist = null, mapping = null, redactSecrets = false) {
 		this.seed = seed != null ? seed : DEFAULT_ANONYMIZE_SEED;
 		this.variance = variance;
 		this.redactSecrets = redactSecrets;
 		this.hints = {};
 		if (hints) {
 			for (const [k, v] of Object.entries(hints)) this.hints[normalizeWord(k)] = v;
 		}
 		this.whitelist = {};
 		if (whitelist) {
 			for (const [k, v] of Object.entries(whitelist)) this.whitelist[normalizeWord(k)] = v;
 		}
 		this.blacklist = new Set();
 		if (blacklist) {
 			for (const b of (Array.isArray(blacklist) ? blacklist : [])) {
 				const n = normalizeWord(b);
 				if (n) this.blacklist.add(n);
 			}
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
		if (typeof value === "number") return null;
		const contextTokens = this._contextTokens(context);
 		const tset = new Set(contextTokens);
		const fieldKey = path?.length ? path[path.length - 1] : "";
 		const fullNorm = normalizeWord(String(fieldKey || ""));
 		// whitelist (highest)
 		if (fullNorm && fullNorm in this.whitelist) {
 			return { type: this.whitelist[fullNorm], confidence: 1 };
 		}
 		for (const token of contextTokens) {
 			if (token in this.whitelist) return { type: this.whitelist[token], confidence: 1 };
 		}
 		// blacklist (preserve)
 		if (fullNorm && this.blacklist.has(fullNorm)) return null;
 		if (Array.from(tset).some(t => this.blacklist.has(t))) return null;
 		// hints override (configurable) -- full norm too
 		if (fullNorm && fullNorm in this.hints && this.hints[fullNorm]) {
 			return { type: this.hints[fullNorm], confidence: 1 };
 		}
 		for (const token of contextTokens) {
 			if (token in this.hints) {
 				const hkind = this.hints[token];
 				if (hkind) return { type: hkind, confidence: 1 };
 			}
 		}
		// email key context
		if (["email", "mail", "bcc", "cc"].some(t => tset.has(t)) && typeof value === "string") {
			return { type: "email", confidence: 0.7 };
		}
		// last_name context (robust)
		if (tset.has("lastname") || tset.has("surname") || tset.has("familyname") || (tset.has("last") && tset.has("name"))) {
			return { type: "last_name", confidence: 0.85 };
		}
		// first_name context (robust)
		if (tset.has("firstname") || tset.has("forename") || tset.has("given") || (tset.has("first") && tset.has("name"))) {
			return { type: "first_name", confidence: 0.8 };
		}
		// middle
		if (tset.has("middle") || tset.has("middlename")) {
			return { type: "first_name", confidence: 0.6 };
		}
		// address
		if ((tset.has("address") || tset.has("street") || tset.has("addr") || tset.has("postaladdress") || (tset.has("line") && tset.has("address"))) && typeof value === "string") {
			return { type: "address", confidence: 0.75 };
		}
		// city/suburb/town/region
		if ((tset.has("city") || tset.has("town") || tset.has("suburb") || tset.has("region")) && typeof value === "string") {
			return { type: "city", confidence: 0.7 };
		}
		// all dates (key date-like + value matches)
		const dateTokens = ["date", "dob", "birthday", "birth", "birthdate", "dateofbirth"];
		const dtTokens = ["datetime", "timestamp", "created", "updated", "modified", "at", "time"];
		if (dateTokens.some(t => tset.has(t)) || dtTokens.some(t => tset.has(t))) {
			const vstr = String(value ?? "");
			if (DATE_RE.test(vstr) || DATETIME_RE.test(vstr)) {
				return { type: "date", confidence: 0.8 };
			}
		}
		// name containing keys -> name or pii_string
		if (tset.has("name") && !Array.from(tset).some(t => NON_PERSON_NAME_CONTEXT_TOKENS.has(t)) && typeof value === "string") {
			if (this._isPersonName(contextTokens, value)) {
				return { type: "name", confidence: 0.8 };
			}
			return { type: "pii_string", confidence: 0.6 };
		}
		if (this._isPersonName(contextTokens, value)) {
			return { type: "name", confidence: 0.8 };
		}
		return null;
	}

	_contextTokens(context) {
		const contextTokens = [];
		for (const token of context) {
			if (typeof token !== "string") continue;
			for (const part of semanticTokens(token)) {
				if (!contextTokens.includes(part)) contextTokens.push(part);
			}
		}
		return contextTokens;
	}

	_isPersonName(contextTokens, value) {
 		if (!this._looksLikePersonName(value)) return false;
 		const tokens = contextTokens.filter(t => !STRUCTURAL_CONTEXT_TOKENS.has(t));
 		if (tokens.some(token => NON_PERSON_NAME_CONTEXT_TOKENS.has(token))) return false;
 		return tokens.some(token => PERSON_NAME_CONTEXT_TOKENS.has(token));
 	}

	_looksLikePersonName(value) {
		if (typeof value !== "string") return false;
		const text = value.trim();
		if (!PERSON_NAME_RE.test(text)) return false;
		if (/^[A-Z]{2,8}$/.test(text)) return false;
		const parts = text.split(" ");
		if (parts.length < 1) return false;
		return parts.every(part => !/\d/.test(part));
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
		const maxTries = 10000;
		while (mapped === value || (mapped in this.reverseValues[kind] && this.reverseValues[kind][mapped] !== value)) {
			salt += 1;
			if (salt > maxTries) {
				const n = await this.deriver.randbelow(0xffffff, kind, value, salt);
				mapped = `Anon-${n.toString(16).padStart(6, "0")}`;
				break;
			}
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
transformer("first_name")(async (self, value, kind, pathKey, reverse) => {
	const p = await getPools();
	return self._mappedValue(kind, value, (salt) => self.deriver.choose(p.firstNames, kind, pathKey, value, salt), reverse);
});
transformer("name")(async (self, value, kind, pathKey, reverse) => self._mappedValue(
	kind,
	value,
	async (salt) => {
		const p = await getPools();
		const orig = String(value ?? "");
		const isSingle = !orig.includes(" ");
		let mapped;
		if (isSingle) {
			mapped = await self.deriver.choose(p.lastNames, kind, pathKey, value, salt, "single");
		} else {
			mapped = `${await self.deriver.choose(p.firstNames, kind, pathKey, value, salt, "first")} ${await self.deriver.choose(p.lastNames, kind, pathKey, value, salt, "last")}`;
		}
		if (orig && mapped) {
			if (orig === orig.toUpperCase()) return mapped.toUpperCase();
			if (isSingle && orig[0] === orig[0].toUpperCase()) {
				return mapped[0].toUpperCase() + (mapped.length > 1 ? mapped.slice(1).toLowerCase() : "");
			}
			if (!isSingle && mapped.includes(" ")) {
				return mapped.split(" ").map(w => w[0].toUpperCase() + w.slice(1).toLowerCase()).join(" ");
			}
		}
		return mapped;
	},
	reverse,
));
transformer("email")(async (self, value, kind, pathKey, reverse) => {
	const p = await getPools();
	return self._mappedValue(kind, value, async (salt) => `${await self.deriver.choose(p.emailUsers, kind, pathKey, value, salt)}${await self.deriver.randbelow(1000, kind, pathKey, value, salt, "n")}@${await self.deriver.choose(p.emailDomains, kind, pathKey, value, salt, "d")}`, reverse);
});
transformer("phone")((self, value, kind, pathKey, reverse) => self._mappedValue(
 	kind,
 	value,
 	async (salt) => {
 		const orig = String(value ?? "");
 		const digitPositions = [];
 		for (let i = 0; i < orig.length; i += 1) {
 			if (/\d/.test(orig[i])) digitPositions.push(i);
 		}
 		const n = digitPositions.length;
 		if (n === 0) return orig;
 		const out = orig.split("");
 		for (let i = 0; i < n; i += 1) {
 			const d = String(await self.deriver.randbelow(10, kind, pathKey, orig, salt, i));
 			out[digitPositions[i]] = d;
 		}
 		return out.join("");
 	},
 	reverse,
 ));

transformer("last_name")(async (self, value, kind, pathKey, reverse) => {
	const p = await getPools();
	return self._mappedValue(kind, value, (salt) => self.deriver.choose(p.lastNames, kind, pathKey, value, salt), reverse);
});

transformer("address")(async (self, value, kind, pathKey, reverse) => {
	const p = await getPools();
	return self._mappedValue(kind, value, async (salt) => {
		const num = 10 + await self.deriver.randbelow(9990, kind, pathKey, value, salt);
		const street = await self.deriver.choose(p.streetNames, kind, pathKey, value, salt);
		return `${num} ${street}`;
	}, reverse);
});

transformer("city")(async (self, value, kind, pathKey, reverse) => {
	const p = await getPools();
	return self._mappedValue(kind, value, (salt) => self.deriver.choose(p.cities, kind, pathKey, value, salt), reverse);
});

transformer("date")((self, value, kind, pathKey, reverse) => self._mappedValue(
	kind,
	value,
 	async (salt) => {
 		const vstr = String(value ?? "").trim();
 		const jitter = Math.max(3, Math.floor(21 * (self.variance || 0.25)));
 		let delta = await self.deriver.randbelow(jitter * 2 + 1, kind, pathKey, value, salt);
 		delta -= jitter;
 		if (delta === 0) delta = (salt % 2 === 0 ? 1 : -1);
 		const timeJitter = Math.max(300, Math.floor(14400 * (self.variance || 0.25)));
 		let secD = await self.deriver.randbelow(timeJitter * 2 + 1, kind, pathKey, value, salt, "time");
 		secD -= timeJitter;
 		if (secD === 0) secD = (salt % 2 === 0 ? 1 : -1);
 		function addDaysToDateStr(iso, days) {
 			// use UTC to avoid local tz shifts
 			const [y, mo, d] = iso.split("-").map(Number);
 			const dt = new Date(Date.UTC(y, mo-1, d));
 			dt.setUTCDate(dt.getUTCDate() + days);
 			const yy = dt.getUTCFullYear();
 			const mm = String(dt.getUTCMonth() + 1).padStart(2, "0");
 			const dd = String(dt.getUTCDate()).padStart(2, "0");
 			return `${yy}-${mm}-${dd}`;
 		}
 		function addJitterToDateTime(vstr, dayDelta, secDelta) {
 			try {
 				if (DATE_RE.test(vstr)) return addDaysToDateStr(vstr, dayDelta);
 				if (DATETIME_RE.test(vstr)) {
 					const m = DATETIME_RE.exec(vstr);
 					if (!m) return vstr;
 					const y = +m[1], mo = +m[2] - 1, d = +m[3];
 					const h = +(m[5] || 0), mi = +(m[6] || 0), s = +(m[7] || 0);
 					let us = 0;
				if (m[8]) us = parseInt((`${m[8].slice(1)}000000`).slice(0, 6), 10);
 					const tz = m[9] || "";
 					const sep = m[4] || "T";
 					const base = Date.UTC(y, mo, d, h, mi, s, Math.floor(us / 1000));
 					const newTime = new Date(base + dayDelta * 86400000 + secDelta * 1000);
 					const yy = newTime.getUTCFullYear();
 					const mm = String(newTime.getUTCMonth() + 1).padStart(2, "0");
 					const dd = String(newTime.getUTCDate()).padStart(2, "0");
 					const hh = String(newTime.getUTCHours()).padStart(2, "0");
 					const mi2 = String(newTime.getUTCMinutes()).padStart(2, "0");
 					const ss2 = String(newTime.getUTCSeconds()).padStart(2, "0");
 					let tstr = `${hh}:${mi2}:${ss2}`;
 					if (m[8]) {
 						const fdigits = m[8].length - 1;
 						let uss = String(Math.floor((newTime.getTime() % 1000) * 1000)).padStart(6, "0").slice(0, fdigits);
 						uss = uss.replace(/0+$/, "");
						if (uss) tstr += `.${uss}`;
 					}
 					return `${yy}-${mm}-${dd}${sep}${tstr}${tz}`;
 				}
 			} catch (_) {}
 			return vstr;
 		}
 		try {
 			if (DATE_RE.test(vstr)) {
 				return addDaysToDateStr(vstr, delta);
 			}
 			if (DATETIME_RE.test(vstr)) {
 				return addJitterToDateTime(vstr, delta, secD);
 			}
 		} catch (_) {}
 		// fallback pure date
 		const fdelta = await self.deriver.randbelow(3650, kind, pathKey, value, salt);
 		return addDaysToDateStr("1990-01-01", Math.abs(fdelta) % 3650);
 	},
	reverse,
));

transformer("pii_string")((self, value, kind, pathKey, reverse) => self._mappedValue(
	kind,
	value,
	async (salt) => {
		const n = await self.deriver.randbelow(16777216, kind, pathKey, value, salt);
		return `[PII-${n.toString(16).padStart(6, "0")}]`;
	},
	reverse,
));

// Public API
export async function anonymize(payload, seed = null, variance = 0.25, hints = null, whitelist = null, blacklist = null, mapping = null, redactSecrets = false) {
 	const a = new Anonymizer(seed, variance, hints, whitelist, blacklist, mapping, redactSecrets);
 	return await a.anonymize(payload);
 }

export async function fuzz(payload, seed = null, variance = 0.25, hints = null, whitelist = null, blacklist = null, mapping = null, redactSecrets = false) {
 	if (seed == null) {
 		seed = Math.floor(Math.random() * 2147483647);
 	}
 	return await anonymize(payload, seed, variance, hints, whitelist, blacklist, mapping, redactSecrets);
 };

export async function deanonymize(payload, seed = null, variance = 0.25, hints = null, whitelist = null, blacklist = null, mapping = null) {
 	const a = new Anonymizer(seed, variance, hints, whitelist, blacklist, mapping);
 	return await a.deanonymize(payload);
 }

export async function redact(payload, seed = null, variance = 0.25, hints = null, whitelist = null, blacklist = null, mapping = null) {
 	return await anonymize(payload, seed, variance, hints, whitelist, blacklist, mapping, true);
 }

export async function guessAnonymizationCategory(fieldName, fieldValue, options = {}) {
 	const { context = null, path = null, hints = null, whitelist = null, blacklist = null } = options;
 	const a = new Anonymizer(null, 0.25, hints, whitelist, blacklist, null, false);
 	const p = path || [fieldName];
 	const c = context || [fieldName];
 	const inf = await a._infer(p, c, fieldValue);
 	return inf ? inf.type : null;
}

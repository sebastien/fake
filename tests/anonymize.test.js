import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { anonymize, deanonymize, redact, guessAnonymizationCategory } from "../src/js/fake/anon.js";
import { preload } from "../src/js/fake/data.js";

await preload();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDir = path.join(__dirname, "data");

async function loadFixtures() {
	const entries = await readdir(dataDir);
	const fixtures = [];
	for (const entry of entries.filter((name) => name.endsWith(".json")).sort()) {
		const payload = JSON.parse(await readFile(path.join(dataDir, entry), "utf8"));
		fixtures.push([entry, payload]);
	}
	return fixtures;
}

function getPath(value, pathValue) {
	return pathValue.split(".").reduce((current, part) => {
		if (Array.isArray(current)) return current[Number(part)];
		return current[part];
	}, value);
}

describe("anonymize fixtures", async () => {
	const fixtures = await loadFixtures();

	test("loads all eight shared fixtures", () => {
		expect(fixtures).toHaveLength(8);
	});

	for (const [name, fixture] of fixtures) {
		test(`${name}: preserves symbol-like values`, async () => {
			const result = await anonymize(fixture.document, 42);
			for (const pathValue of fixture.expectations.symbol_paths) {
				expect(getPath(result.value, pathValue)).toEqual(getPath(fixture.document, pathValue));
			}
		});

		test(`${name}: roundtrip restores the original`, async () => {
			const result = await anonymize(fixture.document, 42);
			const restored = await deanonymize(result.value, 42, 0.25, null, null, null, result.mapping);
			expect(restored).toEqual(fixture.document);
		});

		test(`${name}: mapping has expected shape`, async () => {
			const result = await anonymize(fixture.document, 42);
			expect(result.mapping.version).toBe(3);
			expect(result.mapping.rules).toEqual({ variance: 0.25 });
			expect(result.mapping.seed_fingerprint).toHaveLength(16);
			expect(result.mapping.values).toBeObject();
		});

		test(`${name}: anonymize is deterministic`, async () => {
			const first = await anonymize(fixture.document, 42);
			const second = await anonymize(fixture.document, 42);
			expect(first).toEqual(second);
		});

		test(`${name}: PII fields are anonymized consistently`, async () => {
			const result = name === "secrets.json"
				? await redact(fixture.document, 42)
				: await anonymize(fixture.document, 42);
			for (const pathValue of fixture.expectations.pii_paths) {
				expect(getPath(result.value, pathValue)).not.toEqual(getPath(fixture.document, pathValue));
			}
		});

		test(`${name}: Python and JavaScript outputs are interchangeable`, async () => {
			const jsResult = await anonymize(fixture.document, 42);
			const python = spawnSync(
				"python3",
				[
					"-c",
					[
						"import json, pathlib, sys",
						"sys.path.insert(0, 'src/py')",
						"import fake",
						"fixture = json.load(open(sys.argv[1], encoding='utf-8'))",
						"print(json.dumps(fake.anonymize(fixture['document'], seed=42)))",
					].join("; "),
					path.join(dataDir, name),
				],
				{ cwd: path.join(__dirname, ".."), encoding: "utf8" },
			);
			expect(python.status).toBe(0);
			expect(jsResult).toEqual(JSON.parse(python.stdout));
		});
	}

	test("dates are fuzzed within weeks but not misclassified as phones", async () => {
		const fixture = fixtures.find(([name]) => name === "insurance-policy.json")[1];
		const result = await anonymize(fixture.document, 42);
		expect(result.value.policy.holder.dateOfBirth).not.toBe(fixture.document.policy.holder.dateOfBirth);
		expect(result.value.policy.claimSummary.incidentDate).not.toBe(fixture.document.policy.claimSummary.incidentDate);
		expect(result.value.policy.holder.dateOfBirth).toMatch(/^\d{4}-\d{2}-\d{2}$/);
	});

	test("full-name fields are anonymized conservatively", async () => {
		const payload = {
			preferredName: "Isaac Watts",
			PersonName: "Joanne Watts",
			adviserName: "Ellen Drenon",
			fileName: "Isaac Watts.pdf",
			companyName: "Watts Lending",
			$type: "com.example.PersonName",
		};
		const result = await anonymize(payload, 42);
		expect(result.value.preferredName).not.toBe(payload.preferredName);
		expect(result.value.PersonName).not.toBe(payload.PersonName);
		expect(result.value.adviserName).not.toBe(payload.adviserName);
		expect(result.value.fileName).toBe(payload.fileName);
		expect(result.value.companyName).toBe(payload.companyName);
		expect(result.value.$type).toBe(payload.$type);
	});

	test("hints and pii_string fallback", async () => {
		const payload = {
			NameOfPerson: "WeirdValue123",
			lastName: "Smith",
			someDate: "2020-05-05",
			emailField: "not-an-email",
		};
		const result = await anonymize(payload, 42, 0.25, { NameOfPerson: "pii_string", lastName: "last_name" });
		expect(result.value.NameOfPerson).not.toBe(payload.NameOfPerson);
		expect(result.value.NameOfPerson).toMatch(/^\[PII-/);
		expect(result.value.lastName).not.toBe(payload.lastName);
		expect(result.value.someDate).not.toBe(payload.someDate);
		expect(result.value.emailField).not.toBe(payload.emailField);
  		expect(result.value.emailField).toContain("@");

		// numeric values under email/address/role/history keys must be preserved as-is
		const payload2 = {
			OrganisationGroupAnnualReviewEmailDays: 5,
			PersonAddressHistory: 0,
			AdviserPublicCNARole: "User",
			AdviserDisputeResolutionService: "FDRS",
		};
		const result2 = await anonymize(payload2, 42);
		expect(result2.value.OrganisationGroupAnnualReviewEmailDays).toBe(5);
		expect(result2.value.PersonAddressHistory).toBe(0);
		expect(result2.value.AdviserPublicCNARole).toBe("User");
		expect(result2.value.AdviserDisputeResolutionService).toBe("FDRS");
  	});

 	test("guess, whitelist, blacklist, datetime time jitter", async () => {
 		expect(await guessAnonymizationCategory("PersonLastName", "Miller")).toBe("last_name");
 		expect(await guessAnonymizationCategory("PersonTwoFactorAuthStatus", "Disabled")).toBeNull();
 		expect(await guessAnonymizationCategory("FooStatus", "Bar", { whitelist: { FooStatus: "symbol" } })).toBe("symbol");
 		expect(await guessAnonymizationCategory("SecretField", "val", { blacklist: ["SecretField"] })).toBeNull();

		// numeric and role enums should not be miscategorized
		expect(await guessAnonymizationCategory("OrganisationGroupAnnualReviewEmailDays", 5)).toBeNull();
		expect(await guessAnonymizationCategory("PersonAddressHistory", 0)).toBeNull();
		expect(await guessAnonymizationCategory("AdviserPublicCNARole", "User")).toBeNull();
		// acronym/enum id under service key -> symbol (preserved, not name)
		expect(await guessAnonymizationCategory("AdviserDisputeResolutionService", "FDRS")).toBe("symbol");
  		const p = { created: "2026-04-08T03:12:25.715309Z" };
  		const r = await anonymize(p, 42);
  		expect(r.value.created).not.toBe(p.created);
  		// whitelist preserve
  		const r2 = await anonymize(p, 42, 0.25, null, { created: "symbol" });
  		expect(r2.value.created).toBe(p.created);
  	});

  	test("phone structure is preserved", async () => {
  		const cases = [
  			"232-123-1234",
  			"+1 (321)-1231-12311",
  			"88-81-12-13",
  			"+44 20 7946 0958",
  			"+1 (415) 555-0141",
  			"1234567",
  			"123456789012345",
  		];
  		for (const c of cases) {
  			const res = (await anonymize({ p: c }, 42)).value.p;
  			expect(res).not.toBe(c);
  			expect(res.replace(/\D/g, "").length).toBe(c.replace(/\D/g, "").length);
  			expect(res.replace(/\d/g, "D")).toBe(c.replace(/\d/g, "D"));
  			const mapping = (await anonymize({ p: c }, 42)).mapping;
  			const restored = (await deanonymize({ p: res }, 42, 0.25, null, null, null, mapping)).p;
  			expect(restored).toBe(c);
  		}
  	});
  });

import { describe, expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { anonymize, deanonymize, redact } from "../src/js/fake/anon.js";

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
			const restored = await deanonymize(result.value, 42, 0.25, null, result.mapping);
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

	test("ISO date strings are not treated as phone numbers", async () => {
		const fixture = fixtures.find(([name]) => name === "insurance-policy.json")[1];
		const result = await anonymize(fixture.document, 42);
		expect(result.value.policy.holder.dateOfBirth).toBe(fixture.document.policy.holder.dateOfBirth);
		expect(result.value.policy.claimSummary.incidentDate).toBe(fixture.document.policy.claimSummary.incidentDate);
	});
});

import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "py"))

import fake  # noqa: E402


DATA_DIR = ROOT / "tests" / "data"


def load_fixtures():
	fixtures = []
	for path in sorted(DATA_DIR.glob("*.json")):
		with path.open(encoding="utf-8") as handle:
			fixtures.append((path.name, json.load(handle)))
	return fixtures


def get_path(value, path):
	current = value
	for part in path.split("."):
		if isinstance(current, list):
			current = current[int(part)]
		else:
			current = current[part]
	return current


class AnonymizeFeatureTest(unittest.TestCase):
	maxDiff = None

	def test_fixture_inventory(self):
		fixtures = load_fixtures()
		self.assertEqual(8, len(fixtures))
		for name, fixture in fixtures:
			with self.subTest(name=name):
				self.assertIn("document", fixture)
				self.assertIn("expectations", fixture)
				self.assertIn("symbol_paths", fixture["expectations"])
				self.assertIn("pii_paths", fixture["expectations"])

	def test_symbol_fields_are_preserved(self):
		for name, fixture in load_fixtures():
			original = fixture["document"]
			result = fake.anonymize(original, seed=42)
			anonymized = result["value"]
			for path in fixture["expectations"]["symbol_paths"]:
				with self.subTest(name=name, path=path):
					self.assertEqual(get_path(original, path), get_path(anonymized, path))

	def test_iso_dates_are_not_treated_as_phone_numbers(self):
		fixture = json.loads((DATA_DIR / "insurance-policy.json").read_text(encoding="utf-8"))
		original = fixture["document"]
		result = fake.anonymize(original, seed=42)["value"]
		self.assertEqual(
			original["policy"]["holder"]["dateOfBirth"],
			result["policy"]["holder"]["dateOfBirth"],
		)
		self.assertEqual(
			original["policy"]["claimSummary"]["incidentDate"],
			result["policy"]["claimSummary"]["incidentDate"],
		)

	def test_roundtrip_restores_original_document(self):
		for name, fixture in load_fixtures():
			original = fixture["document"]
			result = fake.anonymize(original, seed=42)
			restored = fake.deanonymize(
				result["value"], seed=42, mapping=result["mapping"]
			)
			with self.subTest(name=name):
				self.assertEqual(original, restored)

	def test_mapping_has_expected_shape(self):
		for name, fixture in load_fixtures():
			redact = name == "secrets.json"
			mapping = fake.anonymize(fixture["document"], seed=42, redact_secrets=redact)["mapping"]
			with self.subTest(name=name):
				self.assertEqual(3, mapping["version"])
				self.assertEqual({"variance": 0.25}, mapping["rules"])
				self.assertEqual(16, len(mapping["seed_fingerprint"]))
				self.assertIsInstance(mapping["values"], dict)
				if name == "secrets.json":
					self.assertTrue(mapping.get("secrets", False))

	def test_anonymize_is_deterministic(self):
		for name, fixture in load_fixtures():
			first = fake.anonymize(fixture["document"], seed=42)
			second = fake.anonymize(fixture["document"], seed=42)
			with self.subTest(name=name):
				self.assertEqual(first, second)

	def test_pii_fields_are_anonymized(self):
		for name, fixture in load_fixtures():
			original = fixture["document"]
			result = fake.anonymize(original, seed=42, redact_secrets=True)
			anonymized = result["value"]
			for path in fixture["expectations"]["pii_paths"]:
				with self.subTest(name=name, path=path):
					self.assertNotEqual(get_path(original, path), get_path(anonymized, path))

	def test_python_and_js_outputs_are_interchangeable(self):
		for name, fixture in load_fixtures():
			python_result = fake.anonymize(fixture["document"], seed=42)
			fixture_path = DATA_DIR / name
			script = """
import { anonymize } from './src/js/fake/anon.js';
import { readFileSync } from 'node:fs';
const fixture = JSON.parse(readFileSync(process.argv[process.argv.length - 1], 'utf8'));
const result = await anonymize(fixture.document, 42);
console.log(JSON.stringify(result));
""".strip()
			completed = subprocess.run(
				["bun", "--input-type=module", "-e", script, str(fixture_path)],
				check=True,
				capture_output=True,
				text=True,
				cwd=str(ROOT),
			)
			js_result = json.loads(completed.stdout)
			with self.subTest(name=name):
				self.assertEqual(python_result, js_result)


if __name__ == "__main__":
	unittest.main()

#!/usr/bin/env python3
# Encoding: utf-8
from pathlib import Path
import re

from setuptools import setup


ROOT = Path(__file__).parent
DATA_PY = ROOT / "src" / "py" / "fake" / "data.py"


def read_version():
	content = DATA_PY.read_text(encoding="utf-8")
	match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
	if not match:
		raise RuntimeError("Could not find VERSION in src/py/fake/data.py")
	return match.group(1)


VERSION = read_version()

setup(
	name             = "fake-data",
	version          = VERSION,
	description      = "Deterministic fake data generator",
	long_description = (ROOT / "README.md").read_text(encoding="utf-8"),
	long_description_content_type = "text/markdown",
	author           = "Sébastien Pierre",
	author_email     = "sebastien.pierre@gmail.com",
	url              = "https://github.com/sebastien/fake",
	download_url     = "https://github.com/sebastien/fake/tarball/%s" % (VERSION),
	keywords         = ["fake", "data", "generator",],
	install_requires = [],
	python_requires  = ">=3.9",
	package_dir      = {"":"src/py"},
	package_data     = {
		"fake.data": ["*.json"],
		"fake.corpus": ["*.xml", "*.txt"],
	},
	include_package_data = True,
	entry_points     = {
		"console_scripts": [
			"fake=fake.cli:main",
		],
	},
	packages         = [
		"fake",
		"fake.data",
		"fake.corpus",
	],
	license          = "BSD-3-Clause",
	classifiers      = [
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3.9",
		"Topic :: Utilities",
		"Development Status :: 4 - Beta",
		"Environment :: Console",
		"Intended Audience :: Developers",
		"Natural Language :: English",
		"Operating System :: POSIX",
	],
)
# EOF - vim: ts=4 sw=4 noet

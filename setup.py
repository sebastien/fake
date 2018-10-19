#!/usr/bin/env python
# Encoding: utf-8
# See: <http://docs.python.org/distutils/introduction.html>
import glob, os
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

VERSION = eval(filter(lambda _:_.startswith("VERSION"),
	file("src/fake/__init__.py").readlines())[0].split("=")[1])

setup(
	name             = "fake-data",
	version          = VERSION,
	description      = "Deterministic fake data generator",
	author           = "Sébastien Pierre",
	author_email     = "sebastien.pierre@gmail.com",
	url              = "http://github.com/sebastien/fake",
	download_url     = "https://github.com/sebastien/fake/tarball/%s" % (VERSION),
	keywords         = ["fake", "data", "generator",],
	install_requires = [],
	package_dir      = {"":"src"},
	package_data     = {"fake.data":[_ for _ in glob.glob("src/fake/data/*.json")]},
	include_package_data = True,
	packages         = [
		"fake",
		"fake.data",
	],
	license          = "License :: OSI Approved :: BSD License",
	classifiers      = [
		"Programming Language :: Python",
		"Topic :: Utilities",
		"Development Status :: 4 - Beta",
		"Environment :: Console",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: BSD License",
		"Natural Language :: English",
		"Topic :: Utilities",
		"Operating System :: POSIX",
		"Programming Language :: Python",
	],
)
# EOF - vim: ts=4 sw=4 noet

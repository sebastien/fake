$(PATH_RUN)/task/project-version-$(VERSION).task:
	@mkdir -p "$(PATH_RUN)/task"
	@perl -0pi -e 's/^VERSION\s*=\s*"[^"]*"/VERSION = "$(VERSION)"/m' src/py/fake/__init__.py
	@perl -0pi -e 's/^const\s+VERSION\s*=\s*"[^"]*"/const VERSION = "$(VERSION)"/m' src/js/fake.js
	@touch "$@"

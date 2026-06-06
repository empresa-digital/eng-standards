CACHE_DIR ?= $(HOME)/.cache/eng-standards
REPO_URL  ?= git@github.com:empresa-digital/eng-standards.git

# Pull latest into the shared cache (clone on first run). Consumers call this from
# their own `make setup`. Always fetches latest; no submodule, no pinning by default.
.PHONY: setup
setup:
	@if [ -d "$(CACHE_DIR)/.git" ]; then \
		echo "Updating eng-standards in $(CACHE_DIR)"; \
		git -C "$(CACHE_DIR)" pull --ff-only --quiet; \
	else \
		echo "Cloning eng-standards into $(CACHE_DIR)"; \
		git clone --quiet "$(REPO_URL)" "$(CACHE_DIR)"; \
	fi

# Validate every YAML file against the rule schema (slice 2: scripts/validate.py).
.PHONY: validate
validate:
	@python3 scripts/validate.py

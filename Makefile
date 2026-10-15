PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
BREAK ?= --break-system-packages

PKGS := packages/spec packages/sim-reference packages/sim-mujoco packages/policies packages/transport packages/evalkit packages/adapters packages/bridges packages/example-suite packages/api packages/cli

.PHONY: install test boundaries

install:
	-$(PIP) uninstall -y loopbench $(BREAK)
	$(PIP) install $(BREAK) pytest httpx
	@for pkg in $(PKGS); do $(PIP) install $(BREAK) -e $$pkg; done

boundaries:
	$(PYTHON) scripts/check_boundaries.py

test: boundaries
	$(PYTHON) -m pytest tests

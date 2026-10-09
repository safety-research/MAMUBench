# Optional convenience targets (`make` is not required). All assume the venv at .venv.
PY ?= .venv/bin/python

.PHONY: test check lint typecheck stats
test:            ## offline suite (no key, no network beyond localhost): eval/ and tests/
	$(PY) -m pytest -n 4 -q
lint:
	.venv/bin/ruff check run.py eval analysis tests && .venv/bin/ruff format --check run.py eval analysis tests
typecheck:
	.venv/bin/pyright --pythonpath $(abspath $(PY))
check: lint typecheck test
stats:           ## every environment's report on its default roots, combined in analysis/out (README.md, Running)
	$(PY) analysis/stats.py

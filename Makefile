PY := PYTHONPATH=src uv run python

pilot:
	$(PY) -m govscore.cli pilot

test:
	PYTHONPATH=src uv run pytest tests/ -q

extract:
	$(PY) -m govscore.cli extract --repo $(REPO)

figures:
	$(PY) -m govscore.figures

lab:
	PYTHONPATH=src uv run jupyter lab

# Reparo do catálogo v2 (decisão 2026-09-13): época → re-pontuação → comparação
# → re-execução das análises. Só git; nenhuma chamada à API no passo central.
repair:
	$(PY) -m govscore.cli epoch
	$(PY) -m govscore.cli rescore
	$(PY) -m govscore.cli compare
	$(PY) -m govscore.cli locus-evidence
	$(PY) -m govscore.cli validate --offline --external-fetched-at 2026-07-24
	$(PY) -m govscore.cli sensitivity
	$(PY) -m govscore.cli robustness
	$(PY) -m govscore.figures

.PHONY: pilot test extract figures lab repair

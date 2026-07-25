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

.PHONY: pilot test extract figures lab

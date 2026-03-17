.PHONY: install dev test lint format clean run install-system

install:
	pip install .

dev:
	pip install -e ".[dev]"

test:
	pytest -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

clean:
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

run:
	nut-up web --host 0.0.0.0 --port 3494 --upsd-host 127.0.0.1 --upsd-port 3493 --state-file ./state.json

install-system:
	bash scripts/install.sh

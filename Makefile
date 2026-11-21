.PHONY: install format fix lint typecheck test quality

install:
	python -m pip install --upgrade pip
	python -m pip install -c constraints/dev.txt -e ".[dev]"
	pre-commit install

format:
	ruff format .

fix:
	ruff check . --fix

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy src tests

test:
	pytest

quality: lint typecheck test

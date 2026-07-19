.PHONY: install format lint typecheck test quality

install:
	python -m pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install

format:
	ruff format .
	ruff check . --fix

lint:
	ruff check .
	ruff format --check .

typecheck:
	mypy src tests

test:
	pytest

quality: lint typecheck test

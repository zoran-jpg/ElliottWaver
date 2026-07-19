# ElliottWaver

ElliottWaver is an Adaptive Market Decision Intelligence Platform.

## Requirements

- Python 3.12
- Git

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Quality gates

```bash
ruff check .
ruff format --check .
mypy src tests
pytest
```

Dependencies point inward. The domain remains independent from brokers, databases, APIs, user interfaces, and AI providers.

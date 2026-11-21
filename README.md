# ElliottWaver

ElliottWaver is an Adaptive Market Decision Intelligence Platform.

## Requirements

- Python 3.12
- Git

## Setup

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -c constraints/dev.txt -e ".[dev]"
pre-commit install
```

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -c constraints/dev.txt -e ".[dev]"
pre-commit install
```

## Reproducible dependencies

- Runtime constraints: `constraints/runtime.txt`
- Development constraints: `constraints/dev.txt` (extends runtime via `-c runtime.txt`)

Runtime-only install:

```bash
python -m pip install -c constraints/runtime.txt .
```

Development install:

```bash
python -m pip install -c constraints/dev.txt -e ".[dev]"
```

## Start desktop MVP

```bash
python -m elliottwaver
```

If installed in editable mode, the console script is also available:

```bash
elliottwaver
```

## Practical chart test (desktop)

1. Start the desktop app.
2. Click "Datei auswahlen".
3. Select `engineering/testdata/swing_e2e_100.csv`.
4. Click "Analyse starten".
5. Verify that result, forecast, and projection sections are populated and that the candlestick chart is visible.
6. Validate viewport controls: pan left/right, zoom in/out, then reset.

## Quality gates

```bash
python -m ruff format .
python -m ruff check .
python -m mypy src tests
python -m pytest
```

## Wheel smoke check

```bash
python -m pip install -c constraints/dev.txt build==1.3.0
python -m build --wheel
python -m venv .wheel-smoke-venv
```

Linux / macOS:

```bash
./.wheel-smoke-venv/bin/python -m pip install dist/*.whl
./.wheel-smoke-venv/bin/python -m pip check
./.wheel-smoke-venv/bin/python engineering/scripts/wheel_smoke.py
```

Windows (PowerShell):

```powershell
.\.wheel-smoke-venv\Scripts\python.exe -m pip install (Get-ChildItem dist\*.whl | Select-Object -First 1).FullName
.\.wheel-smoke-venv\Scripts\python.exe -m pip check
.\.wheel-smoke-venv\Scripts\python.exe engineering/scripts/wheel_smoke.py
```

Dependencies point inward. The domain remains independent from brokers, databases, APIs, user interfaces, and AI providers.

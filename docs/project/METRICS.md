# Project metrics ledger

## Document role

`METRICS.md` stores dated and reproducible quality measurements.
Only executed checks are recorded as confirmed.

## Latest confirmed baseline

### 2026-11-21 (EP-07 local validation)

- Python: 3.12.10
- `python -m ruff format .`: PASS
- `python -m ruff check .`: PASS
- `python -m mypy src tests`: PASS
- `python -m pytest`: 379 passed
- Coverage: 92.57%

## Previous confirmed baseline

### 2026-11-21 (EP-06 local release verification)

- Python: 3.12.10
- `python -m ruff format .`: PASS
- `python -m ruff check .`: PASS
- `python -m mypy src tests`: PASS
- `python -m pytest`: 371 passed
- Coverage: 92.66%
- Wheel build: PASS
- Isolated wheel install: PASS
- `pip check`: PASS
- Wheel smoke script: PASS
- `python -m elliottwaver --help`: PASS

## Historical snapshots

### 2026-07-19 (legacy baseline retained for history)

- `python -m pytest`: 36 passed
- Coverage: 99.02%
- Ruff format/check: PASS
- MyPy: PASS

## Open measurement items

- Real GitHub Actions Linux/Windows matrix execution results are pending and therefore not recorded as completed metrics here.
- Cross-platform release confirmation remains incomplete until that matrix run is executed.

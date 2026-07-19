# Engineering Package Template

## Package identity
- Package ID:
- Title:
- Status:
- Branch:

## Current confirmed state
- Review PROJECT_MANIFEST.md, CURRENT_STATUS.md, ROADMAP.md, and the assigned package record before editing.
- Record confirmed facts only.

## Goal
- Describe the package goal.

## Scope
- Define what is included.
- Explicitly list exclusions.

## Inspect list
- Repository state
- Relevant documentation
- Relevant source files
- Relevant tests

## Create list
- New files to add

## Modify list
- Existing files to change

## Delete list
- Files to remove, if any

## Functional requirements
- What must be implemented?

## Domain invariants
- Describe domain rules and invariants if relevant.

## Architecture constraints
- Preserve dependency boundaries.
- Do not change architecture implicitly.

## Test requirements
- Add or update tests when behavior changes.
- Do not weaken tests.

## Validation commands
- python -m ruff format .
- python -m ruff check .
- python -m mypy src tests
- python -m pytest
- git status

## Acceptance criteria
- Clear checklist of completion conditions.

## Risk assessment
- Note any risks or unknowns.

## Time estimate
- Estimate duration.

## Final report format
- Summary
- Files created
- Files modified
- Validation results
- Follow-up items

## Documentation update requirements
- Update relevant Project Intelligence documents when requested or when the package materially changes state.

## Explicit stop conditions
- Stop before changing architecture or roadmap without explicit approval.
- Stop if validation reveals unresolved issues.
- Do not commit or push.
- Do not automatically begin the next package.

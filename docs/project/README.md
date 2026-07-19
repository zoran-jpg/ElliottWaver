# Project Intelligence

## Purpose

Project Intelligence is the central, version-controlled source of truth for ElliottWaver. It brings together the manifest, roadmap, status, metrics, decisions, and Engineering Package records so the project remains understandable and reviewable as it grows.

## Authoritative documents

- PROJECT_MANIFEST.md: primary source of truth for project identity, architecture, standards, workflow, and current status.
- docs/project/ROADMAP.md: source of truth for planned and completed Engineering Packages.
- docs/project/status/CURRENT_STATUS.md: source of truth for the current operational state.
- docs/project/METRICS.md: confirmed and historical quality measurements.
- docs/project/DECISIONS.md: accepted project decisions and rationale.
- docs/project/engineering-packages/: records for individual Engineering Packages.

## Interaction model

- ChatGPT provides architecture, roadmap guidance, technical direction, reviews, and root-cause analysis.
- GitHub Copilot Agent inspects the repository, implements the assigned package, runs validation, and produces structured reports.
- GitHub stores repository history, workflow automation, issues, pull requests, and releases.
- The user reviews the work, approves progress, and decides when to proceed.

## Documentation update flow

After each Engineering Package, the relevant project-intelligence documents should be updated so that the manifest, roadmap, status, metrics, decisions, and package record remain aligned with the verified state.

## Document map

- Project identity and governance: PROJECT_MANIFEST.md
- Planned work: docs/project/ROADMAP.md
- Current operational state: docs/project/status/CURRENT_STATUS.md
- Quality measurements: docs/project/METRICS.md
- Accepted decisions: docs/project/DECISIONS.md
- Package records: docs/project/engineering-packages/

# Legacy documentation archive

**These files are historical records, not current deployment guidance.**

They were written for earlier states of SmartProp and are preserved here so the
graduation report can cite them. Several describe systems that have since been
replaced:

| Document | What it described | Current state |
|---|---|---|
| `DATABASE_SETUP_LOCAL.md` | Local MySQL setup for the original schema | Superseded by `database/README.md` and `ops/OPERATIONS.md` |
| `GEOSPATIAL_NEXT.md` | Planned geospatial work | Partially implemented; see `docs/` and the GIS modules |
| `LOCATION_LABELS.md` | Location label mapping for the v6 valuation API | Still accurate for v6; see `ai-services/README.md` |
| `MODEL_V6_DIAGNOSTICS.md` | Error analysis of the v6 valuation model | Historical analysis; the model is unchanged |
| `PR4_REVIEW.md` | Review notes for pull request #4 | Historical record of a completed review |
| `VALUATION_HISTORY.md` | Design of the valuation history feature | Implemented; see `V14__valuation_history.sql` |

## Why they are here

The Vue frontend (`frontend/vue.ui`) was replaced by React (`frontend/src`).
These documents were written while the Vue frontend was current, so some
instructions reference paths that no longer exist. They are kept verbatim —
including any stale paths — because altering them would make them useless as
historical evidence.

## What to read instead

- Current setup: `README.md`, `backend/README.md`, `frontend/README.md`
- Operations and backup: `ops/OPERATIONS.md`
- Database: `database/README.md`
- AI services: `ai-services/README.md`
- Architecture map: `docs/PROJECT_MAP.md`

## Provenance

Extracted from `origin/main` at commit `aa30b4e` (2026-10-27) with content
verified byte-identical by SHA-256 before commit. No edits were made.

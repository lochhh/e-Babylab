# CLAUDE.md

## Project
e-Babylab is a Django web application for running unmoderated online experiments. Researchers use the admin UI to design multi-stage experiments; participants run them in a browser. Features include no-code experiment authoring, multimedia stimuli, CDI (Communicative Development Inventory) assessments, and webcam-based eye tracking (WebGazer).

## graphify
- **graphify** (`.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Environment Setup
Requires Docker Desktop.
The dev compose file is `docker-compose.dev.yml`. All Django and pytest commands run inside the container:
```bash
docker compose -f docker-compose.dev.yml exec web <command>
```

Admin UI at `http://localhost:8080/admin/`, pgAdmin at `http://localhost:5050`.

## Tests
Ensure new code is covered by tests. Run existing tests to verify setup and check for regressions. Use test-driven development wherever possible.

### Python (pytest)
Run pytest inside the container. Tests are in `/usr/src/tests/`:
```bash
docker compose -f docker-compose.dev.yml exec web uv run pytest
```

Before writing new fixtures, check for existing ones in `tests/conftest.py`.

Parametrize tests to cover multiple scenarios without duplication. Use `pytest.mark.parametrize` for this.

Inside `tests/data/`, there is a sample participant .xlsx file that is the output file for each participant containing the results from an eye-tracking experiment. There are 4 worksheets in the file:
- "Participant": contains participant data form and CDI form responses
- "Trials": contains trial-level data
- "EyeTrackingData": contains gaze data recorded by WebGazer, each row corresponds to a gaze sample with trial number, time, x/y coordinates
- "EyeTrackingValidation": contains WebGazer validation data

For testing CDI Instruments, use the files in `tests/data/norwegian-ws-production` to create the `Instrument`.

### JavaScript (Vitest + Playwright)
Requires [Node.js](https://nodejs.org/).

Install dependencies once:
```bash
cd tests
npm install
npx playwright install chromium firefox webkit msedge --with-deps
```

Run tests from `tests/`:
```bash
cd tests
npm run test:unit   # Vitest unit tests only (no dev server needed)
npm run test:e2e    # Playwright e2e tests (dev server must be running)
npm test            # both suites in sequence
```

## Architecture
### Experiment data model
The experiment structure is a five-level hierarchy defined in `src/experiments/models.py`:

```
Experiment
  └─ ListItem          (contains ordered sequence of outer blocks)
       └─ OuterBlockItem   (groups blocks; can be randomised or ordered)
            └─ BlockItem       (groups  trials; can be randomised or ordered)
                 └─ TrialItem      (stimulus + response configuration; can be randomised or ordered)
```

`SubjectData` tracks a participant session (UUID-keyed). `TrialResult` records per-trial responses. `CdiResult` stores CDI responses. `Instrument` holds CDI word lists and IRT parameters used by `cdi.py` for adaptive administration via `catsim`.

### Group-based experiment sharing
Experiments and data are shared within Django `Group`s, reflecting real research group boundaries. Users belong to one or more groups; experiments can be restricted to a group. This is a first-class feature — preserve it when refactoring auth or permissions.

### Non-obvious integrations
- **WebGazer** is vendored JS — eye tracking runs entirely client-side.
- **catsim + scipy** power IRT-based adaptive item selection in the CDI flow (`cdi.py`).
- **django-filer** manages media uploads in the admin; file fields on models use `FilerFileField` or `FilerImageField`.

### Settings
All secrets and DB config come from `.env`.

### Static files — two directories, do not confuse them
- **`src/experiments/static/experiments/`** — source JS/CSS tracked in git (Django app static convention). Edit files here.
- **`src/static/`** — `collectstatic` output, gitignored via `src/static/**`. Never edit or commit files here; they are overwritten at deploy time.

When editing frontend JS, always work in `src/experiments/static/experiments/js/`, not `src/static/`.

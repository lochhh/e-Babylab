# CLAUDE.md

## Project

e-Babylab is a Django web application for running unmoderated online experiments. Researchers use the admin UI to design multi-stage experiments; participants run them in a browser. Features include no-code experiment authoring, multimedia stimuli, CDI (Communicative Development Inventory) assessments, and webcam-based eye tracking (WebGazer, beta).

## Environment Setup

Requires Docker Desktop. 
The dev compose file is `docker-compose.dev.yml`. All Django and pytest commands run inside the container:
```bash
docker compose -f docker-compose.dev.yml exec web <command>
```

Admin UI at `http://localhost:8080/admin/`, pgAdmin at `http://localhost:5050`.

## Tests

### Python (pytest)
Run pytest inside the container:
```bash
docker compose -f docker-compose.dev.yml exec web uv run pytest 
```

Before writing new fixtures, check for existing ones in `tests/conftest.py`. 

Inside `tests/data/`, there is a sample participant .xlsx file that is the output file for each participantcontaining the results from an eye-tracking experiment. There are 4 worksheets in the file:
- "Participant": contains participant data form and CDI form responses
- "Trials": contains trial-level data
- "EyeTrackingData": contains gaze data recorded by WebGazer, each row corresponds to a gaze sample with trial number, time, x/y coordinates
- "EyeTrackingValidation": contains WebGazer validation data
Test 

For testing CDI Instruments, use the files in `tests/data/norwegian-ws-production` to create the `Instrument`.

### JavaScript (Vitest)
Requires [Node.js](https://nodejs.org/).

Install dependencies once:
```bash
cd tests/js
npm install
```

Run tests:
```bash
npm test
```

## Modernisation in progress

Existing code is being modernised incrementally — don't treat current patterns as established conventions:

- **Python function/method names** are being migrated to `snake_case` (many are not yet).
- **Docstrings** are being added to all functions/classes (none exist yet, despite ruff `D` rules being active).

When touching existing code, migrate names and add docstrings in the same change. New code should follow standard Python conventions from the start.

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
- **django-filebrowser** manages media uploads in the admin; file fields on models use `FileBrowseField`.

### Settings

All secrets and DB config come from `.env`.

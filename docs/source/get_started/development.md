(target-local-development)=
# Development

If you haven't set up e-Babylab yet, follow the steps in [Getting Started](index.md#try-it-locally) first.

## Additional Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — needed for adding and removing Python dependencies.
- [Node.js](https://nodejs.org/) — needed for running JavaScript and end-to-end tests.

## Pre-commit Hooks

The project uses [pre-commit](https://pre-commit.com/) to run linting and formatting checks before each commit. Install the hooks once after cloning:

```bash
uv tool install pre-commit
pre-commit install
```

## Running Tests

### Python (pytest)

Run the Python test suite inside the Docker container:

```bash
docker compose -f docker-compose.dev.yml exec web uv run pytest
```

### JavaScript (Vitest) and End-to-End Tests (Playwright)

JS tests run directly on your machine (no Docker needed). Requires [Node.js](https://nodejs.org/).

**Install dependencies once** (installs both Vitest and Playwright deps):

```bash
cd tests
npm install
npx playwright install chromium firefox webkit msedge --with-deps
```

**Run tests:**

```bash
cd tests
npm run test:unit   # Vitest unit tests only (no dev server needed)
npm run test:e2e    # Playwright e2e tests (dev server must be running)
npm test            # both suites in sequence
```

**Watch mode** (re-runs unit tests on file change):

```bash
cd tests && npm run test:watch
```

**E2e tests** require the dev server to be running (see [Try It Locally](index.md#try-it-locally)).

**Run a single browser:**

```bash
cd tests/e2e && npx playwright test --project=chromium
```

**Run a single spec:**

```bash
cd tests/e2e && npx playwright test specs/experiment.spec.js --project=chromium
```

**Interactive UI mode:**

```bash
cd tests/e2e && npm run test:ui
```

**Browser coverage:**

| Project        | Browser              | Platform          |
|----------------|----------------------|-------------------|
| `chromium`     | Chrome               | Desktop           |
| `firefox`      | Firefox              | Desktop           |
| `webkit`       | Safari (approximate) | Desktop           |
| `edge`         | Edge                 | Desktop           |
| `mobile-chrome`| Chrome               | Android (Pixel 5) |
| `mobile-safari`| Safari               | iOS (iPhone 14)   |

:::{note}
`mobile-safari` uses WebKit with iPhone 14 device emulation. For the most accurate Safari results, run this project on macOS (CI uses a macOS runner; locally, it works on any platform but macOS gives the closest match to real Safari).
:::

## Database Admin (pgAdmin)

The development environment includes [pgAdmin](https://www.pgadmin.org/) for easy access to the database. It is accessible at `http://localhost:5050`. The default port can be changed by updating the `5050:80` port mapping under the `pgadmin` service in `docker-compose.dev.yml`. Login credentials are set via `PGADMIN_EMAIL` and `PGADMIN_PASSWORD` in `.env`.

## Django Commands

Run Django management commands inside the container:

```bash
docker compose -f docker-compose.dev.yml exec web uv run python manage.py <command> [options]
```

All available commands can be found in the [Django documentation](https://docs.djangoproject.com/en/6.0/ref/django-admin/).

## Managing Dependencies

### Python

`pyproject.toml` is not mounted inside the container, so dependency changes must be made outside it using [uv](https://docs.astral.sh/uv/). The `venv_cache` Docker volume persists the virtual environment across container restarts — simply rebuilding the image is not enough, because the volume overrides the image's venv on startup. You must clear the volume so Docker re-initialises it from the freshly built image.

```bash
# 1. Add or remove the package (updates pyproject.toml and uv.lock)
uv add <package>
uv remove <package>

# 2. Stop containers and remove the venv volume (keeps database intact)
docker compose -f docker-compose.dev.yml down
docker volume rm e-babylab_venv_cache

# 3. Rebuild the image and restart
docker compose -f docker-compose.dev.yml up -d --build

# 4. If the package adds Django apps with migrations, apply them
docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate
```

### JavaScript

Whenever you add, remove, or upgrade a JS dependency, commit the updated `package-lock.json` alongside your `package.json` changes:

```bash
cd tests && npm install
git add tests/package.json tests/js/package.json tests/e2e/package.json tests/package-lock.json
git commit -m "Update JS dependencies"
```

## Data Model Changes

If you make changes to the data models, you will need to create and apply migration files:

```bash
docker compose -f docker-compose.dev.yml exec web uv run python manage.py makemigrations
docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate
```

For more information, see the [Django migrations documentation](https://docs.djangoproject.com/en/6.0/topics/migrations/).

## Docker

### Rebuild the image

Pass `--build` to force Docker to rebuild the `web` image:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Do this after:

- Adding or removing a Python dependency (`pyproject.toml` / `uv.lock` changed)
- Modifying `Dockerfile` (e.g. adding a system package)
- Switching base image or Python version

You do **not** need to rebuild when changing Python source files under `src/` — those are volume-mounted and Django's dev server reloads them automatically.

### Stop e-Babylab

```bash
docker compose -f docker-compose.dev.yml down
```

To stop without destroying the containers:

```bash
docker compose -f docker-compose.dev.yml stop
```

For more information, see [docker compose down](https://docs.docker.com/compose/reference/down/) and [docker compose stop](https://docs.docker.com/compose/reference/stop/).

### View container logs

```bash
docker compose -f docker-compose.dev.yml logs -f web          # follow live output
docker compose -f docker-compose.dev.yml logs --tail=100 web  # last 100 lines
```

### Open a shell inside the container

```bash
docker compose -f docker-compose.dev.yml exec web bash
```

### Restart a service

For example, restart the `web` (Django) service after `.env` changes:

```bash
docker compose -f docker-compose.dev.yml restart web
```

### Wipe and reset the database

:::{danger}
This permanently deletes all data in the dev database.
:::

```bash
docker compose -f docker-compose.dev.yml down -v   # removes containers + named volumes
# optional: remove bind-mounted data
rm -rf media/ webcam/ reports/
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate
docker compose -f docker-compose.dev.yml exec web uv run python manage.py createsuperuser
```

`down -v` removes Docker **named volumes** (`postgres_data_dev`, `venv_cache`) but not bind-mounted directories. The `rm -rf` step is optional — include it to also clear uploaded media, webcam recordings, and reports for a fully clean slate. These directories are recreated automatically when Django needs them.

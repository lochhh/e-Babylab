(target-local-development)=
# Running Locally

## First-Time Setup

If you are running e-Babylab for the first time, execute the following steps in order:

1. Start e-Babylab in development mode:

    ```bash
    docker compose -f docker-compose.dev.yml up -d --build
    ```

2. Set up the database:

    ```bash
    docker compose -f docker-compose.dev.yml exec web python manage.py migrate
    ```

3. Expose static files (e.g. JavaScript files):

    ```bash
    docker compose -f docker-compose.dev.yml exec web python manage.py collectstatic
    ```

4. Create a superuser for logging into the admin interface:

    ```bash
    docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
    ```

Once everything is set up, e-Babylab is accessible at `http://localhost:8080/admin/`.

## Subsequent Runs

For subsequent runs, start e-Babylab using:

```bash
docker compose -f docker-compose.dev.yml up -d
```

## Stopping e-Babylab

Stop e-Babylab with `Ctrl + C` or:

```bash
docker compose -f docker-compose.dev.yml down
```

To stop without destroying the containers:

```bash
docker compose -f docker-compose.dev.yml stop
```

For more information about the differences between these commands, see the documentation for [docker compose down](https://docs.docker.com/compose/reference/down/) and [docker compose stop](https://docs.docker.com/compose/reference/stop/).

## Running Tests

### Python (pytest)

Run the Python test suite inside the Docker container:

```bash
docker compose -f docker-compose.dev.yml exec web uv run pytest
```

### JavaScript (Vitest)

JS unit tests run directly on your machine (no Docker needed). Requires [Node.js](https://nodejs.org/).

Install dependencies once:

```bash
cd tests/js
npm install
```

Run tests:

```bash
npm test
```

To run in watch mode (re-runs on file change):

```bash
npm run test:watch
```

## Database Admin (pgAdmin)

The development environment includes [pgAdmin](https://www.pgadmin.org/) for easy access to the database. It is accessible at `http://localhost:5050`. The default port can be changed by updating the `5050:80` port mapping under the `pgadmin` service in `docker-compose.dev.yml`. Login credentials are set via `PGADMIN_EMAIL` and `PGADMIN_PASSWORD` in `.env`.

## Rebuilding the Image

Pass `--build` to force Docker to rebuild the `web` image:

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

Do this after:

- Adding or removing a Python dependency (`pyproject.toml` / `uv.lock` changed)
- Modifying `Dockerfile` (e.g. adding a system package)
- Switching base image or Python version

**You do not need to rebuild** when changing Python source files under `src/` — those are volume-mounted and Django's dev server reloads them automatically.

## Common Workflows

### View container logs

```bash
# Follow live output
docker compose -f docker-compose.dev.yml logs -f web

# Last 100 lines only
docker compose -f docker-compose.dev.yml logs --tail=100 web
```

### Open a shell inside the container

```bash
docker compose -f docker-compose.dev.yml exec web bash
```

### Restart only the web service (e.g. after .env changes)

```bash
docker compose -f docker-compose.dev.yml restart web
```

### Add a Python dependency

```bash
# 1. Add the package (updates pyproject.toml and uv.lock)
docker compose -f docker-compose.dev.yml exec web uv add <package>

# 2. Rebuild so the next `up` uses the updated lockfile
docker compose -f docker-compose.dev.yml up -d --build
```

### Wipe and reset the database

> **Warning:** This permanently deletes all data in the dev database.

```bash
docker compose -f docker-compose.dev.yml down -v   # removes containers + named volumes
docker compose -f docker-compose.dev.yml up -d --build
docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate
docker compose -f docker-compose.dev.yml exec web uv run python manage.py createsuperuser
```

## Data Model Changes

If you make changes to the data models during development, you will need to create and apply migration files:

```bash
# Create migration files
docker compose -f docker-compose.dev.yml exec web python manage.py makemigrations

# Apply migrations
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
```

For more information, see the [Django migrations documentation](https://docs.djangoproject.com/en/5.2/topics/migrations/).

## Executing Django Commands

To run Django management commands inside the container:

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py <command> [options]
```

All available commands can be found in the [Django documentation](https://docs.djangoproject.com/en/6.0/ref/django-admin/).

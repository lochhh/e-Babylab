(local-development)=
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

## Database Admin (pgAdmin)

The development environment includes [pgAdmin](https://www.pgadmin.org/) for easy access to the database. It is accessible at `http://localhost:5050`. The default port can be changed by updating the `5050:80` port mapping under the `pgadmin` service in `docker-compose.dev.yml`. Login credentials are set via `PGADMIN_EMAIL` and `PGADMIN_PASSWORD` in `.env`.

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

All available commands can be found in the [Django documentation](https://docs.djangoproject.com/en/5.2/ref/django-admin/).

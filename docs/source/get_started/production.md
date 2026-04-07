(target-production)=
# Running in Production

The production environment uses nginx for HTTPS/TLS support.

## Prerequisites

Before starting, you will need to:

1. Create `docker-compose.yml` by copying the template:

    ```bash
    cp docker-compose.yml.template docker-compose.yml
    ```

    Then add valid TLS certificates to the nginx container via volumes in `docker-compose.yml`.

2. Create `nginx.conf` by copying the template:

    ```bash
    cp nginx.conf.template nginx.conf
    ```

    Then replace `<your_domain.com>` with your actual domain.

By default, TLS certificates are expected at:

- `/etc/ssl/certs/cert.pem`
- `/etc/ssl/private/server.key`

These paths can be customised in `nginx.conf`.

## First-Time Setup

If you are running e-Babylab for the first time, execute the following steps in order:

1. Start e-Babylab in production mode:

    ```bash
    docker compose up -d --build
    ```

2. Set up the database:

    ```bash
    docker compose exec web python manage.py migrate
    ```

3. Expose static files (e.g. JavaScript files):

    ```bash
    docker compose exec web python manage.py collectstatic
    ```

4. Create a superuser for logging into the admin interface:

    ```bash
    docker compose exec web python manage.py createsuperuser
    ```

After starting, e-Babylab will be available at `https://<your_domain.com>:8443/admin`.

## Subsequent Runs

For subsequent runs, start e-Babylab using:

```bash
docker compose up -d
```

## Database Admin (pgAdmin)

pgAdmin is included in the production environment but does not expose a public port for security reasons. To access it, use SSH port forwarding from your local machine:

```bash
ssh -L 5050:localhost:5050 user@your-server
```

Then visit `http://localhost:5050` in your browser.

## Executing Django Commands

To run Django management commands inside the container:

```bash
docker compose exec web python manage.py <command> [options]
```

All available commands can be found in the [Django documentation](https://docs.djangoproject.com/en/5.2/ref/django-admin/).

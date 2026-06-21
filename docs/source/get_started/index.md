(target-get-started)=
# Getting Started

## Introduction

Before proceeding, we recommend watching this short introduction video to understand what e-Babylab offers and decide whether it fits your needs.

:::{youtube} Zssrfr0G2Ag
:align: center
:::

## Prerequisites

e-Babylab runs in a containerised environment using Docker and Docker Compose, which are both included in [Docker Desktop](https://docs.docker.com/get-started/get-docker/).

(target-installation)=
## Configure Your Instance

### Get e-Babylab Code

To get started, clone the e-Babylab repository:

```bash
git clone https://github.com/lochhh/e-Babylab.git
```

If you plan to make custom changes to the code, [fork the repository](https://github.com/lochhh/e-Babylab) first, then clone your fork:

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/e-Babylab.git
```

### Set Up Environment Variables

1. In the terminal, navigate to the directory where you cloned or forked the e-Babylab repository:

    ```bash
    cd e-Babylab
    ```

2. Create your `.env` file by copying the template:

    ```bash
    cp .env.template .env
    ```

3. Generate a Django `SECRET_KEY`:

    ```bash
    python -c 'import secrets; print(secrets.token_urlsafe())'
    ```

    Or use an online generator such as [Djecrety](https://djecrety.ir/).

    :::{note}
    If your secret key contains special characters like `$`, `\`, or `` ` ``, Docker will try to interpret them as variable references in the `.env` file. Either wrap the value in single quotes (e.g., `SECRET_KEY='my$ecretKey'`) or regenerate until you get a key without those characters. The `secrets.token_urlsafe()` method above only produces URL-safe characters and avoids this problem.
    :::

4. Copy the generated key and paste it into the `SECRET_KEY` field in your `.env` file.

5. Register for [Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/get-started/widget-management/dashboard/) to obtain the site key and secret key:

    ::::{tab-set}
    :::{tab-item} Local development
    For local development, use [Cloudflare's test keys](https://developers.cloudflare.com/turnstile/troubleshooting/testing/) — no account needed.
    :::
    :::{tab-item} Production
    Go to the [Cloudflare Turnstile dashboard](https://dash.cloudflare.com/?to=/:account/turnstile) and click **Add widget**, then fill in:

    - **Widget name**: e.g. `e-Babylab`
    - **Hostname**: your domain (e.g. `your-domain.com`)

    Leave all other options at their defaults and click **Create** to generate the keys.
    :::
    ::::

6. Copy the site key to `CLOUDFLARE_TURNSTILE_SITE_KEY` and the secret key to `CLOUDFLARE_TURNSTILE_SECRET_KEY` in your `.env` file.

7. The database connection values (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) are pre-filled with defaults that work for local development. If you are deploying to production, make sure to set a strong `DB_PASSWORD`.

## Try It Locally

If you want to try e-Babylab locally before deploying to production, follow these steps:

1. Start e-Babylab in development mode:

    ```bash
    docker compose -f docker-compose.dev.yml up -d --build
    ```

2. Set up the database:

    ```bash
    docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate
    ```

3. Expose static files (e.g. JavaScript files):

    ```bash
    docker compose -f docker-compose.dev.yml exec web uv run python manage.py collectstatic
    ```

4. Create an admin account for logging into the admin interface:

    ```bash
    docker compose -f docker-compose.dev.yml exec web uv run python manage.py createsuperuser
    ```

Once everything is set up, e-Babylab is accessible at `http://localhost:8080/admin/`.

For subsequent runs, start e-Babylab using:

```bash
docker compose -f docker-compose.dev.yml up -d
```

For more information on running tests, managing dependencies, and other development workflows, see the [Development](development.md) guide.

(target-production)=
## Production Deployment

If you have already cloned or forked the repository and configured your `.env` file as described in [Configure Your Instance](#configure-your-instance), you are ready to deploy.

### Configure for Production

In your `.env` file, uncomment and set the following:

1. **Domain and TLS certificates** — set `DOMAIN`, `SSL_CERT_PATH`, and `SSL_KEY_PATH`:

    ```bash
    DOMAIN=your-domain.com
    SSL_CERT_PATH=/etc/ssl/certs/your_cert.pem
    SSL_KEY_PATH=/etc/ssl/private/your_key.key
    ```

2. **Database password** — set a strong `DB_PASSWORD`.

3. **Admin account** (optional) — uncomment `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` to auto-create an admin account on first startup. If you skip this, you can create one manually later:

    ```bash
    docker compose exec web python manage.py createsuperuser
    ```

### Start

```bash
docker compose up -d
```

e-Babylab will be available at `https://your-domain.com/admin/`.

### Database Access

For production database access, use any Postgres client (e.g. psql, pgAdmin, DBeaver) with SSH tunnelling to port 5432 on your server:

```bash
ssh -L 5432:localhost:5432 user@your-server
```

Then connect to `localhost:5432` with the credentials from your `.env` file. pgAdmin is included in the development environment only.

### Executing Django Commands

To run Django management commands inside the container:

```bash
docker compose exec web python manage.py <command> [options]
```

All available commands can be found in the [Django documentation](https://docs.djangoproject.com/en/6.0/ref/django-admin/).

:::{toctree}
:maxdepth: 1
:hidden:

development
:::

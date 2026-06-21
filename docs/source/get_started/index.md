(target-get-started)=
# Getting Started

## Introduction

Before proceeding, we recommend watching this short introduction video to understand what e-Babylab offers and decide whether it fits your needs.

:::{youtube} Zssrfr0G2Ag
:align: center
:::

## Prerequisites

e-Babylab runs in a containerised environment using Docker and Docker Compose, which are both included in [Docker Desktop](https://docs.docker.com/get-started/get-docker/).

## Try It Locally

Run a local instance of e-Babylab for testing or development.

1. Clone the e-Babylab repository:

    ```bash
    git clone https://github.com/lochhh/e-Babylab.git
    cd e-Babylab
    ```

    If you plan to make custom changes to the code, [fork the repository](https://github.com/lochhh/e-Babylab) first, then clone your fork:

    ```bash
    git clone https://github.com/YOUR_GITHUB_USERNAME/e-Babylab.git
    cd e-Babylab
    ```

2. Configure your `.env` file as described in [](target-setup-env).

3. Start e-Babylab in development mode:

    ```bash
    docker compose -f docker-compose.dev.yml up -d --build
    ```

4. Set up the database:

    ```bash
    docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate
    ```

5. Expose static files (e.g. JavaScript files):

    ```bash
    docker compose -f docker-compose.dev.yml exec web uv run python manage.py collectstatic
    ```

6. Create an admin account for logging into the admin interface:

    ```bash
    docker compose -f docker-compose.dev.yml exec web uv run python manage.py createsuperuser
    ```

Once everything is set up, e-Babylab is accessible at `http://localhost:8080/admin/`.

To stop e-Babylab:

```bash
docker compose -f docker-compose.dev.yml down
```

For more information on running tests, managing dependencies, and other development workflows, see the [Development](development.md) guide.

(target-production)=
## Production Deployment

Deploy e-Babylab to a production server.

1. Create the `e-Babylab` directory and download the required files:

    ```bash
    mkdir e-Babylab && cd e-Babylab
    curl -LO https://raw.githubusercontent.com/lochhh/e-Babylab/main/docker-compose.yml
    curl -LO https://raw.githubusercontent.com/lochhh/e-Babylab/main/.env.template
    curl -LO https://raw.githubusercontent.com/lochhh/e-Babylab/main/nginx.conf.template
    ```

2. Configure your `.env` file as described in [](target-setup-env), then uncomment and set the following production values:

    - **Domain and TLS certificates** — you will need a domain name pointing to your server and a TLS certificate. Obtain these from your institution's IT department or a provider such as [Let's Encrypt](https://letsencrypt.org/). Then set `DOMAIN`, `SSL_CERT_PATH`, and `SSL_KEY_PATH`:

        ```bash
        DOMAIN=your-domain.com
        SSL_CERT_PATH=/etc/ssl/certs/your_cert.pem
        SSL_KEY_PATH=/etc/ssl/private/your_key.key
        ```

    - **PostgreSQL data directory** — `POSTGRES_DATA_PATH` defaults to `./postgres_data`. Change it to an SSD-backed path for better I/O performance if available.

    - **Database password** — set a strong `DB_PASSWORD`.

    - **Admin account** (optional) — set `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` to auto-create an admin account on first startup. If you skip this, you can create one manually later:

        ```bash
        docker compose exec web python manage.py createsuperuser
        ```

3. Start e-Babylab:

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

(target-setup-env)=
## Set Up Environment Variables

1. Create your `.env` file by copying the template:

    ```bash
    cp .env.template .env
    ```

2. Generate a Django `SECRET_KEY`:

    ```bash
    python -c 'import secrets; print(secrets.token_urlsafe())'
    ```

    Or use an online generator such as [Djecrety](https://djecrety.ir/).

    :::{note}
    If your secret key contains special characters like `$`, `\`, or `` ` ``, Docker will try to interpret them as variable references in the `.env` file. Either wrap the value in single quotes (e.g., `SECRET_KEY='my$ecretKey'`) or regenerate until you get a key without those characters. The `secrets.token_urlsafe()` method above only produces URL-safe characters and avoids this problem.
    :::

3. Copy the generated key and paste it into the `SECRET_KEY` field in your `.env` file.

4. Register for [Cloudflare Turnstile](https://developers.cloudflare.com/turnstile/get-started/widget-management/dashboard/) to obtain the site key and secret key:

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

5. Copy the site key to `CLOUDFLARE_TURNSTILE_SITE_KEY` and the secret key to `CLOUDFLARE_TURNSTILE_SECRET_KEY` in your `.env` file.

6. The database connection values (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) are pre-filled with defaults that work for local development. If you are deploying to production, make sure to set a strong `DB_PASSWORD`.

:::{toctree}
:maxdepth: 1
:hidden:

development
:::

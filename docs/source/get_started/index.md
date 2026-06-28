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

    - **e-Babylab version** (optional) — `IMAGE_TAG` defaults to `latest`. Set it to a specific [release](https://github.com/lochhh/e-Babylab/releases) version (e.g. `2.0.0`) to pin the deployment.

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

### Updating

A GitHub Actions workflow builds and pushes a new Docker image on every push to `main` and on [version releases](https://github.com/lochhh/e-Babylab/releases). The image tag is configurable via `IMAGE_TAG` in `.env` (defaults to `latest`).

:::{note}
Releases before v2.0.0 are not compatible with this deployment method.
:::

To update to a specific release (e.g. `v2.0.0`):

```bash
cd /path/to/e-Babylab

# Download config files matching the release
curl -Lo docker-compose.yml.new \
  https://raw.githubusercontent.com/lochhh/e-Babylab/v2.0.0/docker-compose.yml
curl -Lo nginx.conf.template.new \
  https://raw.githubusercontent.com/lochhh/e-Babylab/v2.0.0/nginx.conf.template
curl -Lo .env.template.new \
  https://raw.githubusercontent.com/lochhh/e-Babylab/v2.0.0/.env.template

# Review changes before applying
diff docker-compose.yml docker-compose.yml.new
diff nginx.conf.template nginx.conf.template.new
diff .env .env.template.new
# Add any new variables from .env.template.new to your .env
mv docker-compose.yml.new docker-compose.yml
mv nginx.conf.template.new nginx.conf.template
rm .env.template.new

# Set the image tag in .env
IMAGE_TAG=2.0.0

# Pull and restart
docker compose pull
docker compose up -d
docker compose exec web python manage.py migrate
```

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

4. Configure a CAPTCHA provider (see [](target-captcha-config) below).

5. The database connection values (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) are pre-filled with defaults that work for local development. If you are deploying to production, make sure to set a strong `DB_PASSWORD`.

(target-captcha-config)=
### CAPTCHA Configuration

CAPTCHA protects the participant form from automated submissions that can pollute your study data. We recommend keeping CAPTCHA enabled in production. Disabling it (`CAPTCHA_PROVIDER=none`) is suitable for development and testing but leaves your study open to automated submissions in production.

Set `CAPTCHA_PROVIDER` in your `.env` file to one of the following:

| | ALTCHA (default) | Turnstile | TrustSig | None |
|---|---|---|---|---|
| **Compliance** | Universal (self-hosted, no data leaves your server) | US-based | EU-based (Germany) | N/A |
| **User friction** | Invisible (proof-of-work) | Low (checkbox) | Invisible (hardware signals) | None |
| **Third-party data** | None | Cloudflare (US) | TrustSig (EU) | None |
| **Cookies** | Zero | Some | Zero | None |
| **Cost** | [Free forever (MIT)](https://altcha.org/) | [Free](https://www.cloudflare.com/en-gb/products/turnstile/) | [Free 50k/mo, then from €9/mo](https://trustsig.eu/#pricing) | Free |
| **Best for** | GDPR/privacy-first deployments | Zero server maintenance, easy setup | EU institutions wanting invisible protection | Dev/testing only |

::::{tab-set}
:::{tab-item} ALTCHA (recommended)
Self-hosted proof-of-work — no third-party requests, no cookies, universally compliant with GDPR, CCPA, LGPD, and PIPL. No account needed.

```bash
CAPTCHA_PROVIDER=altcha
ALTCHA_HMAC_KEY=<generate with: openssl rand -hex 32>
```
:::
:::{tab-item} Turnstile
Cloudflare's checkbox-style CAPTCHA. Easy setup, zero server maintenance.

Register at the [Cloudflare Turnstile dashboard](https://dash.cloudflare.com/?to=/:account/turnstile), click **Add widget**, enter your domain, and copy the keys. For local development, use [Cloudflare's test keys](https://developers.cloudflare.com/turnstile/troubleshooting/testing/).

```bash
CAPTCHA_PROVIDER=turnstile
CLOUDFLARE_TURNSTILE_SITE_KEY=<your site key>
CLOUDFLARE_TURNSTILE_SECRET_KEY=<your secret key>
```
:::
:::{tab-item} TrustSig
Invisible hardware-signal bot protection, hosted in Germany (EU). Zero cookies, GDPR compliant.

Register at [trustsig.eu](https://trustsig.eu/) and copy the keys from your dashboard. Add your production domain to the Allowed Domains list.

```bash
CAPTCHA_PROVIDER=trustsig
TRUSTSIG_SITE_KEY=<your pk_live_ key>
TRUSTSIG_SECRET_KEY=<your sk_live_ key>
```
:::
:::{tab-item} None
Disable CAPTCHA entirely. Only use for development/testing.

```bash
CAPTCHA_PROVIDER=none
```
:::
::::

:::{toctree}
:maxdepth: 1
:hidden:

development
:::

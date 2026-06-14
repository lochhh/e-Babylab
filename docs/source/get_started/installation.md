(target-installation)=
# Installation

## Get e-Babylab Code

To get started, you will need a copy of the e-Babylab code. You can either:

- **Clone** the repository if you just want to try e-Babylab locally, without any modifications, or
- **Fork** the repository if you plan to run your own production instance or make custom changes — this lets you keep track of your own customisations and changes to the code, while still being able to pull in updates from the original repository.

To clone the repository, run the following command in the terminal:

```bash
git clone https://github.com/lochhh/e-Babylab.git
```

To fork the repository, go to the [e-Babylab repository](https://github.com/lochhh/e-Babylab) and click **Fork**. This will create a copy of the repository under your own GitHub account, which you can then clone using:

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/e-Babylab.git
```

## Install Docker Desktop

e-Babylab runs in a containerised environment using Docker and Docker Compose, which are both included in [Docker Desktop](https://docs.docker.com/get-started/get-docker/). No other software is required.

## Configure Your Instance

To set up e-Babylab, you will need to define values specific to your own instance in a `.env` file.

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

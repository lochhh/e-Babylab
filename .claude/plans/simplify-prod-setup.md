# Simplify Production Setup & Reorganise Docs

## Context

The production setup previously required 8 manual steps: clone the repo, copy 3 template files, manually edit domain/cert placeholders, build the image from source, then run migrate/collectstatic/createsuperuser. This work reduces it to: fill in `.env`, run `docker compose up`.

## Status

All commits are on the `prod-image` branch. Remaining work:
- [ ] Verify prod compose works locally with self-signed certs
- [ ] Deploy and test on an NREC instance
- [ ] Test GHCR publish workflow via `workflow_dispatch` after merging
- [ ] Push branch and create PR

## Deployment Testing on NREC

### Local verification with self-signed certs

1. Generate a self-signed certificate:

    ```bash
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout server.key -out cert.pem -subj '/CN=localhost'
    ```

2. Set the following in `.env`:

    ```
    DOMAIN=localhost
    SSL_CERT_PATH=./cert.pem
    SSL_KEY_PATH=./server.key
    ```

3. Start the prod stack:

    ```bash
    docker compose -f docker-compose.prod.yml up -d
    ```

4. Visit `https://localhost/admin/` (browser will warn about self-signed cert — expected).

### NREC instance (no domain)

1. SSH into the NREC instance and install Docker.

2. Clone the repo (or copy the deployment files: `docker-compose.prod.yml`, `nginx.conf.template`, `.env.template`).

3. Generate a self-signed certificate using the instance's IP:

    ```bash
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout server.key -out cert.pem -subj '/CN=<NREC_IP>'
    ```

4. Set the following in `.env`:

    ```
    DOMAIN=<NREC_IP>
    SSL_CERT_PATH=./cert.pem
    SSL_KEY_PATH=./server.key
    DB_PASSWORD=<strong-password>
    ```

5. Optionally set `DJANGO_SUPERUSER_*` vars for auto-creating an admin account.

6. Start the prod stack:

    ```bash
    docker compose -f docker-compose.prod.yml up -d
    ```

7. Visit `https://<NREC_IP>/admin/` and verify:
   - Nginx serves HTTPS with the self-signed cert
   - Migrations ran automatically (check logs: `docker compose -f docker-compose.prod.yml logs web`)
   - Static files are served correctly
   - Admin login works (superuser was auto-created or create one manually)

## Commits

### 1. `02ce875` Add production entrypoint with auto-migrate and superuser
- New `src/docker-entrypoint.sh`: waits for DB, runs migrate, collectstatic, optional createsuperuser, then execs gunicorn
- Dockerfile prod stage: added ENTRYPOINT/CMD, fixed `COPY ./src ./` with `--no-install-project`
- `.env.template`: added optional `DJANGO_SUPERUSER_*` vars

### 2. `e850616` Parameterise prod config with env vars and add pgAdmin auto-config
- Replaced `docker-compose.yml.template` with `docker-compose.prod.yml`
- Env var interpolation for `DOMAIN`, `SSL_CERT_PATH`, `SSL_KEY_PATH`
- Standard ports 80/443 instead of 8080/8443
- nginx.conf.template uses `${DOMAIN}` with auto-envsubst
- Pre-built GHCR image instead of building from source
- Removed pgAdmin from prod compose (dev only)
- Added `pgadmin-servers.json` for dev pgAdmin auto-config
- Renamed legacy `/ipl/` paths to `/app/`
- Fixed deprecated `http2` nginx directive
- Cleaned up `.env.template` (removed misleading comments, dev-only pgAdmin defaults)

### 3. `bc0deb8` Restrict ALLOWED_HOSTS to DOMAIN env var in production
- `settings.py`: `ALLOWED_HOSTS = [os.getenv("DOMAIN", "localhost")]` in prod

### 4. `70338f2` Add GitHub Actions workflow to publish Docker image to GHCR
- `.github/workflows/publish.yaml`: builds and pushes to `ghcr.io/lochhh/e-babylab`
- Tags: `:latest` on main, `:X.Y.Z` and `:X.Y` on version tags

### 5. `7ef4132` Reorganise Getting Started into a single page
- Merged `installation.md` + `production.md` into `index.md`
- Renamed `local-development.md` to `development.md`
- Flow: Prerequisites → Configure → Try Locally → Production Deployment

### 6. `5487272` Improve development guide structure and content
- Added prerequisites (uv, Node.js) and pre-commit hooks section
- Reordered: tests → pgAdmin → Django commands → dependencies → data models → Docker
- Removed duplicate content, fixed stale links, Django 6.0 docs consistently

### 7. `be5ef0f` Fix test to match ALLOWED_HOSTS change in production settings

### 8. `79f5a26` Add pytest example for running a specific test file

## Key Decisions Made During Implementation

- **Single Dockerfile** for dev and prod (multi-stage: `base` for dev, `prod` for prod)
- **`--no-install-project`** in prod stage (Django doesn't need to be installed as a package)
- **pgAdmin removed from prod**, kept in dev with auto-registered server via `servers.json`
- **Clone recommended for all users** (fork only if making custom changes)
- **Self-signed cert instructions** for local prod verification without a real domain
- **UK English** throughout all docs and commit messages

# e-Babylab NREC Hosting Plan

> **For agentic workers:** This is an infrastructure/operations plan. Follow tasks sequentially — each depends on the previous. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy e-Babylab on NREC using Docker Compose (nginx + Django + PostgreSQL), served over HTTPS on standard ports 80/443 with a UiO-issued SSL certificate.

**Architecture:** Single Ubuntu 24.04 VM running Docker Compose. Docker image is built locally (manually, during dev phase) and pushed to `ghcr.io`; the server pulls the pre-built image — no build tools or source code on the server. When the app is stable, a GitHub Actions workflow replaces the manual push step. SSD volume (50 GB) stores PostgreSQL data for fast I/O. Regular volume (500 GB) stores config files, media uploads, webcam recordings, and reports. SSL certificate ordered from UiO IT services (valid 1–2 years, manual renewal).

**Quota used:** 1 instance (4 cores, 16 GB RAM), 50 GB SSD, 500 GB regular storage.

> **Why not more cores?** gunicorn workers = 2×CPU+1, so 4 cores → 9 workers → ~9 concurrent requests, sufficient for 50–100 simultaneous participants. RAM is the real bottleneck: more RAM = more workers you can safely configure + more PostgreSQL cache. `m1.xlarge` (4 cores, 16 GiB) beats `c1.xlarge` (4 cores, 8 GiB) for this workload. If you later need higher concurrency, add gunicorn workers via `--workers` flag or stand up a second instance.

---

## Critical Files (in repo)
- `docker-compose.yml.template` → copy to `docker-compose.yml` (not committed)
- `nginx.conf.template` → copy to `nginx.conf` (not committed)
- `.env.template` → copy to `.env` (not committed)
- `docs/source/get_started/production.md` — existing production guide

---

## Phase 1: NREC Dashboard Setup

> All steps in the browser at https://dashboard.nrec.no/

### Task 1: Log In and Select Region

- [ ] Go to https://dashboard.nrec.no/
- [ ] Log in with your institution credentials (Feide/Dataporten)
- [ ] In the top bar, select your **Project** from the dropdown (your new NREC project)
- [ ] Choose **Region**: `BGO` (Bergen) or `OSL` (Oslo) — pick one and stay consistent throughout. BGO is recommended if your collaborators are in Bergen/western Norway; OSL otherwise.

---

### Task 2: Upload SSH Key Pair

- [x] Navigate to **Project → Compute → Key Pairs**
- [x] Click **Import Public Key**
- [x] **Key Pair Name**: e.g. `e-babylab-key`
- [x] **Key Type**: SSH Key
- [x] Paste your **public key** (contents of `~/.ssh/id_ed25519.pub` or `~/.ssh/id_rsa.pub`)
- [x] Click **Import Key Pair**

> If you don't have an SSH key yet, run locally first:
> ```bash
> ssh-keygen -t ed25519 -C "e-babylab-nrec"
> cat ~/.ssh/id_ed25519.pub
> ```

---

### Task 3: Create Security Group

- [ ] Navigate to **Project → Network → Security Groups**
- [ ] Click **Create Security Group**
  - **Name**: `e-babylab-sg`
  - **Description**: `e-Babylab web + SSH access`
- [ ] Click **Create Security Group** — you land on the rules page

Add the following ingress rules (click **Add Rule** for each):

**Rule 1 — SSH (restrict to your IP):**
- Rule: `SSH`
- Direction: Ingress
- Remote: CIDR
  - **IPv4**: set Ether Type to `IPv4`, enter `<your-ip>/32` — e.g. `84.212.100.5/32`
  - **IPv6**: set Ether Type to `IPv6`, enter `<your-ip>/128` — e.g. `2001:db8:abcd:1234::1/128`
  - Find your IP at https://ifconfig.me/ — format tells you which type you have
  - Note: home/office IPs can change — update the rule when your IP rotates

> **If your IP is IPv6:** also SSH to the instance's **IPv6** address (not IPv4). Both addresses shown in **Project → Compute → Instances** IP column.

**Rule 2 — HTTP (public, for Let's Encrypt challenge + redirect):**
- Rule: `HTTP`
- Direction: Ingress
- Remote: CIDR → `0.0.0.0/0`

**Rule 3 — HTTPS (public):**
- Rule: `HTTPS`
- Direction: Ingress
- Remote: CIDR → `0.0.0.0/0`

**Rule 4 — ICMP/ping (IPv4, public):**
- Rule: `All ICMP`
- Direction: Ingress
- Remote: CIDR → `0.0.0.0/0`

**Rule 5 — ICMP/ping (IPv6, public):**
- Rule: `All ICMP` (IPv6)
- Direction: Ingress
- Remote: CIDR → `::/0`

> Egress rules (all outbound) are already present by default. Do not delete them.

---

### Task 4: Create Volumes

#### 4a — SSD Volume (PostgreSQL)

- [ ] Navigate to **Project → Volumes → Volumes**
- [ ] Click **Create Volume**
  - **Volume Name**: `e-babylab-db`
  - **Description**: `PostgreSQL data — SSD`
  - **Volume Source**: No source, empty volume
  - **Type**: `mass-storage-ssd`
  - **Size (GiB)**: `50`
  - **Availability Zone**: `nova`
- [ ] Click **Create Volume**

#### 4b — Regular Volume (media/data)

- [ ] Click **Create Volume** again
  - **Volume Name**: `e-babylab-data`
  - **Description**: `Media files, repo, webcam, reports`
  - **Volume Source**: No source, empty volume
  - **Type**: `mass-storage-default`
  - **Size (GiB)**: `500`
  - **Availability Zone**: `nova`
- [ ] Click **Create Volume**

---

### Task 5: Launch the Instance

- [ ] Navigate to **Project → Compute → Instances**
- [ ] Click **Launch Instance**

**Details tab:**
- **Instance Name**: `e-babylab`
- **Description**: `e-Babylab production server`
- **Availability Zone**: default
- **Count**: 1

**Source tab:**
- **Select Boot Source**: Image
- **Create New Volume**: No (use ephemeral disk for OS)
- Search for and select: **`GOLD Ubuntu 24.04 LTS`**

**Flavor tab:**
- Select **`m1.xlarge`** (4 vCPUs, 16 GiB RAM, 20 GiB disk)
  > 4 cores gives gunicorn ~9 sync workers — sufficient for 50–100 concurrent participants. The 16 GiB RAM lets you scale workers further if needed and gives PostgreSQL a larger shared_buffers cache. If you need more cores (e.g. 100+ simultaneous participants), contact NREC support for a custom flavor — standard flavors top out at 4 vCPUs within a 10-core project quota.

**Networks tab:**
- Select **`dualStack`** only (gives public IPv4 + IPv6)
  > Do **not** select more than one network — instance will not work correctly.

**Security Groups tab:**
- Remove `default` if present
- Add `e-babylab-sg` (the group you just created)

**Key Pair tab:**
- Select `e-babylab-key` (the key you imported)

**Configuration / other tabs:** leave defaults.

- [ ] Click **Launch Instance**
- [ ] Wait ~60 seconds for status to show `Running`

---

### Task 6: Attach Volumes to Instance

#### 6a — Attach SSD volume

- [ ] Navigate to **Project → Volumes → Volumes**
- [ ] Find `e-babylab-db` → click the **dropdown arrow** → **Manage Attachments**
- [ ] **Attach To Instance**: select `e-babylab`
- [ ] Leave device name as suggested (e.g. `/dev/sdb`)
- [ ] Click **Attach Volume**

#### 6b — Attach regular data volume

- [ ] Find `e-babylab-data` → **Manage Attachments**
- [ ] Attach to `e-babylab`, device `/dev/sdc`
- [ ] Click **Attach Volume**

---

### Task 7: Get Public IP Address

With **dualStack** network, public IPv4 assigned directly — no floating IP needed.

- [ ] Navigate to **Project → Compute → Instances**
- [ ] Note IP shown in IP column for `e-babylab` — this is public IPv4
- [ ] Use this IP for DNS records (Task 8) and SSH access (Task 9)

---

### Task 8: Set Up DNS Zone

You need a domain name. Two options:

**Option A — Register a domain (any registrar):**
- Register e.g. `yourlabname.no` or `.com` at Namecheap/Gandi/etc.
- Point nameservers to NREC:
  - `ns1.nrec.no`
  - `ns2.nrec.no`
- Then in the NREC dashboard:
  - Navigate to **DNS → Zones** → **Create Zone**
  - **Name**: `yourdomain.com.` (trailing dot required)
  - **Email**: your email
  - After creation, click **Create Record Set**:
    - Type: `A`, Name: `@`, Records: `<your floating IP>`
    - Type: `A`, Name: `www`, Records: `<your floating IP>`

**Option B — uiocloud.no subdomain (UiO users only):**
- Email hostmaster@usit.uio.no: request delegation of `yourlab.uiocloud.no` to your NREC project
- After delegation, add A record in NREC DNS → Zones as above

> DNS propagation can take up to 1 hour after creating the A record. You need the domain resolving to your floating IP **before** ordering the UiO SSL certificate (Task 13). Plan ahead.

---

## Phase 2: Server Provisioning (SSH)

> All steps below run on the NREC VM via SSH.

### Task 9: Connect and Prepare the System

- [ ] SSH into the instance:
  ```bash
  ssh ubuntu@<your-floating-ip>
  ```
  Expected: Ubuntu 24.04 welcome banner.

- [ ] Update packages:
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```

- [ ] Install required tools:
  ```bash
  sudo apt install -y git curl snapd
  ```

---

### Task 10: Install Docker

- [ ] Install Docker via the official script:
  ```bash
  curl -fsSL https://get.docker.com | sudo sh
  ```

- [ ] Add your user to the docker group (avoids needing `sudo` for every docker command):
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```

- [ ] Verify Docker works:
  ```bash
  docker run --rm hello-world
  ```
  Expected: `Hello from Docker!`

---

### Task 11: Mount Volumes

#### 11a — Identify block devices

- [ ] Check which devices are attached:
  ```bash
  lsblk
  ```
  Expected output (approximate):
  ```
  NAME   MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
  vda    252:0    0   20G  0 disk
  └─vda1 252:1    0   20G  0 part /
  vdb    252:16   0   50G  0 disk          ← SSD (e-babylab-db)
  vdc    252:32   0  500G  0 disk          ← regular (e-babylab-data)
  ```

#### 11b — Format and mount SSD (first time only)

- [ ] Format:
  ```bash
  sudo mkfs.ext4 /dev/vdb
  ```
- [ ] Create mount point and mount:
  ```bash
  sudo mkdir -p /mnt/ssd
  sudo mount /dev/vdb /mnt/ssd
  ```
- [ ] Create PostgreSQL data directory:
  ```bash
  sudo mkdir -p /mnt/ssd/postgres_data
  ```

#### 11c — Format and mount regular volume (first time only)

- [ ] Format:
  ```bash
  sudo mkfs.ext4 /dev/vdc
  ```
- [ ] Create mount point and mount:
  ```bash
  sudo mkdir -p /mnt/data
  sudo mount /dev/vdc /mnt/data
  sudo chown -R $USER:$USER /mnt/data /mnt/ssd
  ```

#### 11d — Make mounts persistent across reboots

- [ ] Get UUIDs:
  ```bash
  sudo blkid /dev/vdb /dev/vdc
  ```
  Example output:
  ```
  /dev/vdb: UUID="a1b2c3d4-..." TYPE="ext4"
  /dev/vdc: UUID="e5f6a7b8-..." TYPE="ext4"
  ```

- [ ] Add to `/etc/fstab` (replace UUIDs with your actual values):
  ```bash
  echo "UUID=<vdb-uuid>  /mnt/ssd   ext4  defaults  0 2" | sudo tee -a /etc/fstab
  echo "UUID=<vdc-uuid>  /mnt/data  ext4  defaults  0 2" | sudo tee -a /etc/fstab
  ```

- [ ] Verify fstab is correct (this remounts all fstab entries):
  ```bash
  sudo mount -a
  df -h /mnt/ssd /mnt/data
  ```
  Expected: both mount points show correct sizes (50G and 500G).

---

## Phase 3: e-Babylab Deployment

### Task 12: Build and Push Docker Image (Manual — Dev Phase)

> Do this step from your **local development machine**. Test the image locally first; only push when it runs without errors.

- [ ] Build the production image locally and verify it starts:
  ```bash
  docker build --target prod -t ghcr.io/lochhh/e-babylab:latest .
  docker run --rm ghcr.io/lochhh/e-babylab:latest python manage.py --version
  ```
  Expected: prints the Django version without errors.

- [ ] Log in to GitHub Container Registry:
  ```bash
  gh auth token | docker login ghcr.io -u lochhh --password-stdin
  ```
  Expected: `Login Succeeded`

- [ ] Push the image:
  ```bash
  docker push ghcr.io/lochhh/e-babylab:latest
  ```
  Expected: layers push, ends with `latest: digest: sha256:...`

- [ ] Make the package public (one-time, so the server can pull without auth):
  - Go to `https://github.com/lochhh?tab=packages`
  - Click `e-babylab` → **Package settings** → change visibility to **Public**

> **When the app is stable:** add `.github/workflows/publish.yml` (see Appendix at the bottom of this plan) to automate this manual push on every `main` merge.

---

### Task 12b: Set Up Deployment Directory on the Server

The server only needs config files and data directories — no full repo clone.

- [ ] SSH into the server, create the deployment directory on the data volume:
  ```bash
  mkdir -p /mnt/data/e-babylab
  cd /mnt/data/e-babylab
  mkdir -p media webcam reports
  ```

- [ ] Download the three config templates from the repo:
  ```bash
  wget -O docker-compose.yml.template \
    https://raw.githubusercontent.com/lochhh/e-Babylab/main/docker-compose.yml.template
  wget -O nginx.conf.template \
    https://raw.githubusercontent.com/lochhh/e-Babylab/main/nginx.conf.template
  wget -O .env.template \
    https://raw.githubusercontent.com/lochhh/e-Babylab/main/.env.template
  ```

---

### Task 13: Obtain SSL Certificate from UiO

UiO issues server certificates via its IT selvbetjening portal. The process is: generate a CSR on the server → submit to UiO → receive cert files → place on server.

#### 13a — Generate private key and CSR on the server

- [ ] SSH into the instance and run:
  ```bash
  sudo mkdir -p /etc/ssl/private /etc/ssl/certs
  sudo openssl req -newkey rsa:4096 -keyout /etc/ssl/private/server.key \
    -out /tmp/server.csr -nodes \
    -subj "/C=NO/ST=Oslo/L=Oslo/O=YourInstitution/CN=yourdomain.com"
  ```
  Expected: generates `/etc/ssl/private/server.key` and `/tmp/server.csr`

- [ ] Copy the CSR content to submit to UiO:
  ```bash
  cat /tmp/server.csr
  ```

#### 13b — Order the certificate from UiO

- [ ] Go to the UiO IT certificate portal (ask your UiO contact for the URL, or check https://www.uio.no/tjenester/it/sikkerhet/sertifikater/)
- [ ] Submit the CSR content from step 13a
- [ ] Select domain: `yourdomain.com`
- [ ] Wait for UiO to issue the certificate (typically same-day to 1–2 business days)

#### 13c — Install the certificate files

- [ ] Download the issued certificate from UiO (you'll receive a `.pem` or `.crt` file, possibly with a separate chain/intermediate)
- [ ] Copy to the server (from your local machine):
  ```bash
  scp yourdomain.pem ubuntu@<your-floating-ip>:/tmp/cert.pem
  scp chain.pem ubuntu@<your-floating-ip>:/tmp/chain.pem   # if provided separately
  ```
- [ ] On the server, create the full chain file (cert + intermediates):
  ```bash
  # If UiO provided a combined fullchain file:
  sudo cp /tmp/cert.pem /etc/ssl/certs/cert.pem

  # If cert and chain are separate, concatenate them:
  sudo cat /tmp/cert.pem /tmp/chain.pem | sudo tee /etc/ssl/certs/cert.pem
  ```
- [ ] Verify the cert and key match (both outputs must be identical):
  ```bash
  openssl x509 -noout -modulus -in /etc/ssl/certs/cert.pem | openssl md5
  openssl rsa  -noout -modulus -in /etc/ssl/private/server.key | openssl md5
  ```
  Expected: same MD5 hash on both lines.

- [ ] Restrict key permissions:
  ```bash
  sudo chmod 640 /etc/ssl/private/server.key
  sudo chown root:ssl-cert /etc/ssl/private/server.key 2>/dev/null || sudo chmod 600 /etc/ssl/private/server.key
  ```

> **Renewal reminder:** UiO certs are valid for 1–2 years. Set a calendar reminder before expiry. Repeat steps 13a–13c, then `docker compose restart nginx`.

---

### Task 14: Configure docker-compose.yml

- [ ] Copy the template:
  ```bash
  cp docker-compose.yml.template docker-compose.yml
  ```

- [ ] Make the following changes to `docker-compose.yml` (edit with `nano docker-compose.yml`):

  **1. Change port mapping to standard 80/443** (find `ports:` under the `nginx:` service):
  ```yaml
  ports:
    - "80:80"
    - "443:443"
  ```

  **2. Update SSL cert paths** (find the nginx volumes — replace `<your_ssl_cert.pem>` lines with the actual host paths from Task 13):
  ```yaml
  - /etc/ssl/certs/cert.pem:/etc/ssl/certs/cert.pem:ro
  - /etc/ssl/private/server.key:/etc/ssl/private/server.key:ro
  ```

  **3. Replace `build:` with pre-built image** (under the `web:` service, remove the `build:` block and replace with):
  ```yaml
  image: ghcr.io/lochhh/e-babylab:latest
  ```

  **4. Use SSD volume for PostgreSQL** (find `postgres_data:/var/lib/postgresql` under the `db:` service volumes):
  ```yaml
  - /mnt/ssd/postgres_data:/var/lib/postgresql/data
  ```
  Then remove the `postgres_data:` entry from the top-level `volumes:` section at the bottom of the file (delete `postgres_data:` and any sub-keys under it).

  > The media, webcam, and reports directories (`./media`, `./webcam`, `./reports`) are already bind-mounted from the current directory, which is on the regular volume. No changes needed there.

---

### Task 15: Configure nginx.conf

- [ ] Copy the template:
  ```bash
  cp nginx.conf.template nginx.conf
  ```

- [ ] Replace the placeholder domain (use `sed`):
  ```bash
  sed -i 's/<your_domain\.com>/yourdomain.com/g' nginx.conf
  ```

- [ ] Verify the replacement:
  ```bash
  grep "server_name" nginx.conf
  ```
  Expected: lines showing `yourdomain.com` not `<your_domain.com>`.

---

### Task 16: Configure .env

- [ ] Copy the template:
  ```bash
  cp .env.template .env
  ```

- [ ] Generate a Django secret key:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(50))"
  ```
  Copy the output.

- [ ] Edit `.env`:
  ```bash
  nano .env
  ```
  Fill in all fields:
  ```
  SECRET_KEY=<paste generated key>
  GOOGLE_RECAPTCHA_SITE_KEY=<from console.cloud.google.com>
  GOOGLE_RECAPTCHA_SECRET_KEY=<from console.cloud.google.com>
  DB_NAME=e_babylab
  DB_USER=e_babylab
  DB_PASSWORD=<generate a strong password>
  DB_HOST=db
  DB_PORT=5432
  PGADMIN_EMAIL=<your email>
  PGADMIN_PASSWORD=<generate a strong password>
  ```

  > For reCAPTCHA keys: go to https://www.google.com/recaptcha/admin/, register site with domain `yourdomain.com`, choose reCAPTCHA v3.

---

### Task 17: Set DJANGO_ENV for Production

- [ ] Confirm `DJANGO_ENV=prod` is set. Check settings.py uses it:
  ```bash
  grep -n "DJANGO_ENV" src/config/settings.py
  ```
  Expected: line showing `if os.environ.get("DJANGO_ENV") == "prod":` or similar.

- [ ] Add to `.env`:
  ```
  DJANGO_ENV=prod
  ```

---

### Task 18: Start Services

- [ ] Pull the pre-built image and start all containers:
  ```bash
  docker compose pull
  docker compose up -d
  ```
  Expected: Docker pulls `ghcr.io/lochhh/e-babylab:latest`, then all 4 containers start (`nginx`, `web`, `db`, `pgadmin`).

- [ ] Check all containers are running:
  ```bash
  docker compose ps
  ```
  Expected: all services show `Up`.

- [ ] Check Django logs for errors:
  ```bash
  docker compose logs web --tail=50
  ```
  Expected: gunicorn worker startup messages, no Python tracebacks.

---

### Task 19: Initialize Database

- [ ] Run migrations:
  ```bash
  docker compose exec web python manage.py migrate
  ```
  Expected: `Applying ... OK` for each migration.

- [ ] Collect static files:
  ```bash
  docker compose exec web python manage.py collectstatic --noinput
  ```
  Expected: `X static files copied to ...`

- [ ] Create admin superuser:
  ```bash
  docker compose exec web python manage.py createsuperuser
  ```
  Follow prompts: enter username, email, password.

---

## Phase 4: Verification

### Task 20: Test the Application

- [ ] HTTP redirect works:
  ```bash
  curl -I http://yourdomain.com
  ```
  Expected: `301 Moved Permanently` → `https://yourdomain.com`

- [ ] HTTPS loads correctly:
  ```bash
  curl -I https://yourdomain.com/admin/
  ```
  Expected: `200 OK` or `301` → login page.

- [ ] Open in browser: `https://yourdomain.com/admin/`
  - Log in with superuser credentials
  - Confirm admin dashboard loads

- [ ] Check SSL certificate:
  ```bash
  curl -v https://yourdomain.com 2>&1 | grep "SSL certificate"
  ```
  Expected: `SSL certificate verify ok`

- [ ] Test pgAdmin via SSH tunnel (from your local machine):
  ```bash
  ssh -L 5050:localhost:5050 ubuntu@<your-floating-ip>
  ```
  Then open `http://localhost:5050` in browser — log in with `PGADMIN_EMAIL` / `PGADMIN_PASSWORD`.

---

## Ongoing Maintenance

### Start/stop

```bash
# From /mnt/data/e-babylab
docker compose up -d        # start
docker compose down         # stop (preserves volumes/data)
```

### Updates (deploy new version)

```bash
# Dev phase (manual): on your local machine, build + push a tested image
docker build --target prod -t ghcr.io/lochhh/e-babylab:latest .
docker push ghcr.io/lochhh/e-babylab:latest

# On the server: pull and restart
cd /mnt/data/e-babylab
docker compose pull
docker compose up -d
docker compose exec web python manage.py migrate   # only if there are new migrations
```

> Once the app is stable, add the GitHub Actions workflow (see Appendix) to automate the build+push step.

### Backup database

```bash
docker compose exec db pg_dump -U e_babylab e_babylab > backup_$(date +%Y%m%d).sql
```

### View logs

```bash
docker compose logs -f web    # Django
docker compose logs -f nginx  # nginx
```

### Expand storage when the 500 GB data volume fills up

You have 1000 GB regular storage quota but only allocated 500 GB. Two options:

**Option A — Extend the existing volume (recommended):**

1. Email support@nrec.no: request that `e-babylab-data` be extended to e.g. 900 GB.
2. Once NREC confirms, stop the app: `docker compose down`
3. Detach the volume in the dashboard: **Volumes → Manage Attachments → Detach**
4. In the dashboard, the new size may already show. If not, NREC may extend it via their backend.
5. Re-attach the volume: **Volumes → Manage Attachments → Attach to e-babylab**
6. SSH in and extend the filesystem (no reformatting needed):
   ```bash
   sudo resize2fs /dev/vdc
   df -h /mnt/data    # verify new size
   ```
7. Restart: `docker compose up -d`

**Option B — Add a second data volume (no downtime for the existing volume):**

1. In the dashboard: create a new volume `e-babylab-data2`, 500 GB, `mass-storage-default`
2. Attach to the instance, format and mount:
   ```bash
   sudo mkfs.ext4 /dev/vdd
   sudo mkdir -p /mnt/data2
   sudo mount /dev/vdd /mnt/data2
   sudo chown -R ubuntu:ubuntu /mnt/data2
   ```
3. Add to `/etc/fstab` (get UUID via `sudo blkid /dev/vdd`):
   ```bash
   echo "UUID=<vdd-uuid>  /mnt/data2  ext4  defaults  0 2" | sudo tee -a /etc/fstab
   ```
4. Move future experiment media directories there and symlink, or update `MEDIA_ROOT` in Django settings to point to the new mount.

> **NREC object storage is not recommended** for production media — it is a pilot service explicitly unsuitable for high-volume or mission-critical data.

---

## Appendix: GitHub Actions Publish Workflow (add when app is stable)

When ready to automate image builds, create `.github/workflows/publish.yml` in the repo:

```yaml
name: Build and push Docker image

on:
  push:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4

      - name: Log in to Container registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=raw,value=latest,enable={{is_default_branch}}
            type=sha

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          target: prod
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

After adding this workflow, the manual `docker build + push` from Task 12 is no longer needed — every merge to `main` triggers an automatic build and push.

Also update the maintenance "Updates" section: `docker compose pull && docker compose up -d` on the server remains the same.

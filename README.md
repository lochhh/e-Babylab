# e-Babylab
e-Babylab [(Lo et al., 2023)](https://link.springer.com/article/10.3758/s13428-023-02200-7) is an open source authoring tool that allows users or researchers to easily create, host, run, and manage online experiments, without writing a single line of code. Using this tool, experiments can be programmed to include any combinations of image, audio, and/or video contents as stimuli and record key presses, clicks, screen touches, audio, video, and eye gaze[^1]. Short-form versions of the MacArthur–Bates Communicative Development Inventories (CDIs; [Chai et al., 2020](https://doi.org/10.1044/2020_JSLHR-20-00361); [Mayor & Mani, 2019](https://doi.org/10.3758/s13428-018-1146-0)) can additionally be included in experiments, allowing users or researchers to collect CDI data online. 

[^1]: Online webcam eye-tracking is currently under beta testing. This feature is implemented based on WebGazer [(Papoutsaki et al., 2016)](https://jeffhuang.com/papers/WebGazer_IJCAI16.pdf) and allows self-calibration using participants' gaze to better suit e-Babylab's use with young children.

## Contents
1. [Installation](#1-installation)
2. [Executing Django Commands](#2-executing-django-commands)
3. [Upgrade](#3-upgrade)
4. [Troubleshooting](#4-troubleshooting)
5. [Useful Links](#5-useful-links)

## 1. Installation
> [!TIP]
> 
> We recommend forking the e-Babylab repository. 
> This will allow you to pull the latest changes from the main repository, whilst keeping your settings and customisations intact.

### Requirements
e-Babylab runs in a containerised environment using Docker and Docker Compose. No other software is required.

To install Docker, please follow the instructions below:
* **Linux:** [Docker](https://docs.docker.com/engine/installation/), [Docker Compose](https://docs.docker.com/compose/install/)
* **Windows:** [Docker for Windows](https://docs.docker.com/docker-for-windows/install/) (includes Docker Compose)
* **Mac:** [Docker for Mac](https://docs.docker.com/docker-for-mac/install/) (includes Docker Compose)

For development, we recommend you to study the [Docker](https://docs.docker.com/get-started/) and [Docker Compose](https://docs.docker.com/compose/gettingstarted/) documentation.

### Define User-Specific Variables
To set up e-Babylab, there are 3 variables (i.e., the Django SECRET KEY, the reCAPTCHA SITE KEY, and the reCAPTCHA SECRET KEY) specific to your own instance of e-Babylab, which you will have to define in a *.env* file:

1. Create your `.env` file by copying `.env.template`. Make sure that this file is in the same directory as `.env.template`.
2. Create your own Django SECRET KEY using `python -c 'import secrets; print(secrets.token_urlsafe())'` or use [Djecrety](https://djecrety.ir/). 
3. Go to [Google reCAPTCHA](https://www.google.com/recaptcha/about/) and click on "[v3 Admin Console](https://www.google.com/recaptcha/admin)". Sign in with a Google account and fill out the site registration form.
4. Provide a **label** (e.g., e-Babylab).
5. Select `reCAPTCHA v3` as **reCAPTCHA type**.
6. If you are running e-Babylab in a local development environment, add `localhost` to **Domains**, otherwise (i.e., running in production) add your own domain, e.g., *your_domain.com*. You can update and add new domains as needed later on.
7. When you are done, click on "Submit" and you will have your **site key** and **secret key**.
8. Copy the **site key** to `GOOGLE_RECAPTCHA_SITE_KEY` and the **secret key** to `GOOGLE_RECAPTCHA_SECRET_KEY` in your `.env` file.

### Run Local Development Environment
> [!IMPORTANT] 
> If you are running e-Babylab for the first time, you will need to:
>
> 1. Allow permissions to execute the `ipl/wait-for-it.sh` script using `chmod +x ipl/wait-for-it.sh`.
> 2. Run the development version of e-Babylab using `docker-compose -f docker-compose.dev.yml up -d`
> 3. Set up the database using `docker-compose -f docker-compose.dev.yml exec web python manage.py migrate`. 
> 4. Expose new static files (e.g., JavaScript files) using `docker-compose -f docker-compose.dev.yml exec web python manage.py collectstatic`.
> 5. Create a superuser (for logging into the admin interface) using `docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser`.

Once everything is set up, e-Babylab can be accessed at `http://localhost:8080/admin/`.

For subsequent runs, you can start e-Babylab using:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

The development environment additionally installs pgadmin for easy access to the database. It will be accessible via a random
port on your system. You can use `docker ps -a` to find out about the port. pgadmin is then at `http://localhost:PORT/login`.
You can find the credentials for pgadmin in the `docker-compose.dev.yml` file.

If you have made any changes to the data models during development, you will need to create migration files and apply these afterwards. Migration files can be created using `docker-compose -f docker-compose.dev.yml exec web python manage.py makemigrations` and applied using `docker-compose -f docker-compose.dev.yml exec web python manage.py migrate`. For more information about migrations, please refer to the [Django documentation](https://docs.djangoproject.com/en/3.1/topics/migrations/).

e-Babylab can be stopped using `Ctrl + C` or `docker-compose -f docker-compose.dev.yml down`. 
To stop e-Babylab without destroying the containers, use `docker-compose -f docker-compose.dev.yml stop`.
For more information about their differences, please refer to the documentation for [docker-compose down](https://docs.docker.com/compose/reference/down/) and [docker-compose stop](https://docs.docker.com/compose/reference/stop/).

### Run in Production
The production environment of e-Babylab additionally uses nginx for HTTPS/TLS support. You will need to:

1. Create `docker-compose.yml` by copying `docker-compose.yml.template` and add valid TLS certificates to the nginx container via volumes in `docker-compose.yml`.
2. Create `nginx.conf` by copying `nginx.conf.template` and replace `<your_domain.com>` with your actual domain.

By default, the TLS certificates are expected to be at the following locations:

* `/etc/ssl/certs/cert.pem`
* `/etc/ssl/private/server.key`

The locations can be customised in the nginx config `nginx.conf`.

> [!IMPORTANT] 
> As mentioned in the previous section, if you are running e-Babylab for the first time, you will need to:
>
> 1. Allow permissions to execute the `ipl/wait-for-it.sh` script using `chmod +x ipl/wait-for-it.sh`.
> 2. Run e-Babylab using `docker-compose up -d`
> 3. Set up the database using `docker-compose exec web python manage.py migrate`. 
> 4. Expose new static files (e.g., JavaScript files) using `docker-compose exec web python manage.py collectstatic`.
> 5. Create a superuser (for logging into the admin interface) using `docker-compose exec web python manage.py createsuperuser`.

After starting, e-Babylab will be available at `https://<your_domain.com>:8443/admin`. 

For subsequent runs, you can start e-Babylab using:
```bash
docker-compose up -d
```

## 2. Executing Django Commands
You can use the following commands to execute commands inside the Django container:

```bash
docker-compose exec web django-admin <command> [options]
docker-compose exec web python manage.py <command> [options]
```

These can be used, for example, to perform upgrades or to create superusers. All available commands can be found [here](https://docs.djangoproject.com/en/3.1/ref/django-admin/).

## 3. Upgrade
To upgrade an existing environment to the latest version of e-Babylab, please follow the steps below:
1. To pull the latest changes from the repository, run `git pull`.
2. To upgrade, we first need to recreate all containers, so that they are using the latest version of e-Babylab. Follow these steps:
    - Shut down the environment using `docker-compose down`. This will remove all containers, but retain the volumes which contain all of your data.
    - Run `docker-compose build` to force a rebuild of the e-Babylab container.
    - Restart the environment using `docker-compose up -d`.
3. Next you need to perform the database migration. You can apply all migrations using `docker-compose exec web python manage.py migrate`.
4. To expose new static files (e.g., JavaScript files), run `docker-compose exec web python manage.py collectstatic`.

To upgrade the database to a newer version, please follow the steps below:
1. Backup your database to a `.sql` file named `all_db.sql` using `docker-compose exec db pg_dumpall -U postgres > /path/to/all_db.sql`.
2. Stop the running containers using `docker-compose down`.
3. Rename the old database directory to `postgres-data.old` using `mv postgres-data postgres-data.old`.
4. Restart the containers using `docker-compose up -d`.
5. Copy the backup file into the running database container (e.g. `e-babylab-db-1`) using `docker cp /path/to/all_db.sql e-babylab-db-1:./all_db.sql`
6. Restore the database using `docker-compose exec db psql -U postgres -f ./all_db.sql`
7. Update the password for the `postgres` user: 
   - `docker-compose exec db psql -U postgres`
   - `\password` to change the password.
   - Enter the new password and confirm it. This needs to be the same as `POSTGRES_PASSWORD` in the `docker-compose.yml` file and `DATABASES['PASSWORD']` in the `ipl/ipl/settings.py` file.
   - `\q` to exit. 
8. Restart the containers using `docker-compose down` and `docker-compose up -d`.

## 4. Troubleshooting

### Web Container starts with `"exec: \"./wait-for-it.sh\": permission denied"`
Allow the execution of the *wait-for-it.sh* script by executing the following command:
`chmod +x ipl/wait-for-it.sh`

### `"Server error (500)"` when attempting to download results
Make sure that there is a "webcam" directory in the "ipl" directory (where manage.py and the Dockerfile are located). If it does not exist, create one. 

### `"Can't find a suitable configuration file in this directory or any parent. Are you in the right directory?"`
Docker is unable to locate `docker-compose.yml`. Either create this file (by copying `docker-compose.yml.template`) or run `docker-compose` commands with `-f docker-compose.dev.yml` (e.g., `docker-compose -f docker-compose.dev.yml build`). 

### `"invalid reCAPTCHA"` at Demographic Data page
From *15.05.2021* onwards, reCAPTCHA verification is required in the Demographic Data (i.e., Participant Form) page. Experiments created *before 15.05.2021* do not have reCAPTCHA in the Demographic Data page template. To add this, you will need to copy and paste the HTML code of the Demographic Data page template of a new experiment: 

1. Create a new experiment.
2. Navigate to the Demographic Data page template.
3. Open the *source code view* (accessed via the "<>" icon on the toolbar).
4. Copy the HTML code and paste this to the Demographic Data page template of your experiment and modify the text accordingly.

## 5. Useful Links
* [e-Babylab User Manual](https://github.com/lochhh/e-Babylab/wiki)
* [HandBrake](https://handbrake.fr/) (for resizing video files and converting .webm to other formats) 
* [Django Tutorial](https://docs.djangoproject.com/en/3.1/intro/overview/)
* [Django with Docker](https://docs.docker.com/compose/django/)

This software is licensed under the [Apache 2 License](https://www.apache.org/licenses/LICENSE-2.0).

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
### Get e-Babylab Code
To get started, you will need a copy of the e-Babylab code. You can either:

- **clone** the repository if you just want to try e-Babylab locally, without any modifications, or 
- **fork** the repository if you plan to run your own production instance or make custom changes---this lets you keep track of your own customisations and changes to the code, while still being able to pull in updates from the original repository.

To clone the repository, run the following command in the terminal:
```bash
git clone https://github.com/lochhh/e-Babylab.git
```
To fork the repository, go to the [e-Babylab repository](https://github.com/lochhh/e-Babylab) and click "Fork".
This will create a copy of the repository under your own GitHub account, which you can then clone using:
```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/e-Babylab.git
```

### Install Docker Desktop
e-Babylab runs in a containerised environment using Docker and Docker Compose, which are both included in [Docker Desktop](https://docs.docker.com/get-started/get-docker/). No other software is required.

### Define Instance-Specific Values
To set up e-Babylab, you will need to define three values that are specific to your own instance of e-Babylab in a `.env` file:
- the Django SECRET KEY, 
- the reCAPTCHA SITE KEY, and 
- the reCAPTCHA SECRET KEY

1. In the terminal, navigate to the directory where you cloned or forked the e-Babylab repository:
    ```bash
    cd e-Babylab
    ```
2. Create your `.env` file by copying the template:
    ```bash
    cp .env.template .env
    ```
3. Generate a Django SECRET KEY:
    ```bash
    python -c 'import secrets; print(secrets.token_urlsafe())'
    ```
    Or use an online generator such as [Djecrety](https://djecrety.ir/).
4. Copy the generated key and paste it into the `SECRET_KEY` field in your `.env` file.
5. Register for Google reCAPTCHA v3 to obtain the SITE KEY and SECRET KEY:
    - Go to the [reCAPTCHA admin console](https://www.google.com/recaptcha/admin/create)
    - Login and register a new site with:
        - **Label**: e.g. `e-Babylab`
        - **reCAPTCHA type**: `Score based (v3)`
        - **Domains**: `localhost` for local development, or your own domain, e.g. `your-domain.com` for production
        - **Project name**: e.g. `e-Babylab`
    - Click on "Submit" to create the reCAPTCHA keys.
6. Copy the SITE KEY to the `GOOGLE_RECAPTCHA_SITE_KEY` field and the SECRET KEY to the `GOOGLE_RECAPTCHA_SECRET_KEY` field in your `.env` file.

### Run Local Development Environment
> [!IMPORTANT] 
> If you are running e-Babylab for the first time, you will need to execute the following commands in the terminal:
>
> 1. Start e-Babylab in development mode:
> ```bash
> docker-compose -f docker-compose.dev.yml up -d
> ```
> 2. Set up the database:
> ```bash
> docker-compose -f docker-compose.dev.yml exec web python manage.py migrate
> ``` 
> 3. Expose new static files (e.g., JavaScript files):
> ```bash
> docker-compose -f docker-compose.dev.yml exec web python manage.py collectstatic
> ```
> 4. Create a superuser for logging into the admin interface:
> ```bash
> docker-compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
> ```

Once everything is set up, e-Babylab can be accessed at `http://localhost:8080/admin/`.

For subsequent runs, you can start e-Babylab using:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

The development environment additionally installs [pgadmin](https://www.pgadmin.org/) for easy access to the database. 
It will be accessible via a random port on your system. You can use `docker ps -a` to find the port and visit pgadmin at `http://localhost:PORT/login`.
The credentials for pgadmin are in `docker-compose.dev.yml`.

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
> As mentioned in the previous section, if you are running e-Babylab for the first time, you will need to execute the following commands in the terminal:
>
> 1. Start e-Babylab in development mode:
> ```bash
> docker-compose -f docker-compose.yml up -d
> ```
> 2. Set up the database:
> ```bash
> docker-compose -f docker-compose.yml exec web python manage.py migrate
> ``` 
> 3. Expose new static files (e.g., JavaScript files):
> ```bash
> docker-compose -f docker-compose.yml exec web python manage.py collectstatic
> ```
> 4. Create a superuser for logging into the admin interface:
> ```bash
> docker-compose -f docker-compose.yml exec web python manage.py createsuperuser
> ```

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
```bash
chmod +x ipl/wait-for-it.sh
```

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

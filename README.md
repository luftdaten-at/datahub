# luftdaten-datahub

## About luftdaten-datahub
luftaten-datahub is an open source plattform build on the Django Web Framework. It is an citizen science tool to explore air quality data measured by Luftdaten.at devices and other sources.

## Contributing

We use GitHub Flow for our development process. Follow these steps to commit your changes:

### 1. Fork the Repository

First, fork the repository to your own GitHub account:

1. Navigate to the [main repository](https://github.com/luftdaten-at/datahub.git).
2. Click the "Fork" button in the upper right corner of the repository page.
3. This creates a copy of the repository in your GitHub account.

### 2. Clone the Forked Repository

Clone your forked repository to your local machine:

```sh
git clone https://github.com/your-username/datahub.git
cd datahub
```

### 3. Create a Branch

Create a new branch to work on your changes. Use the following naming convention: `feature/{issue-number}-{issue-name}`. 

For example, if you are working on issue #123 to add user authentication, you would name your branch:

```sh
git checkout -b feature/123-add-user-authentication
```

### 4. Make Your Changes

Make your changes to the codebase. Ensure you:

- Write clear and concise commit messages.
- Test your changes thoroughly.
- Follow the coding standards and guidelines of the project.

### 5. Commit Your Changes

Commit your changes to the branch:

```sh
git add .
git commit -m "Description of your changes"
```

### 6. Push to Your Fork

Push your changes to your forked repository on GitHub:

```sh
git push origin feature/123-add-user-authentication
```

### 7. Open a Pull Request

Navigate to the main repository on GitHub, and you should see a prompt to open a pull request for your branch. Click "Compare & pull request":

1. Provide a clear and concise title for the pull request.
2. Include a detailed description of your changes and any relevant information.
3. Reference the issue number in the description using keywords like `fixes`, `closes`, or `resolves` followed by the issue number (e.g., `fixes #123`).
4. Request a review from the repository maintainers.

### 8. Review Process

Your pull request will be reviewed by the maintainers. Be prepared to make additional changes based on their feedback. Once approved, your changes will be merged into the main branch.

### 9. Keep Your Fork Up-to-Date

To keep your fork updated with the latest changes from the main repository, add the original repository as a remote and pull the latest changes:

```sh
git remote add upstream https://github.com/luftdaten-at/datahub.git
git fetch upstream
git checkout main
git merge upstream/main
```

### 10. Delete Your Branch

After your pull request has been merged, you can safely delete your branch:

```sh
git branch -d feature/123-add-user-authentication
git push origin --delete feature/123-add-user-authentication
```

By following these steps, you can contribute effectively using GitHub Flow. Thank you for your contributions!


## Documentation

### Development
Development version:

    docker compose up -d
    docker compose exec app python manage.py migrate
    docker compose exec app python manage.py createsuperuser

If you don't have a `.env` file yet, copy it from the template: `cp project.env .env`.

**Shortcut:** run manage.py via the app container with:

    ./manage <command>

Examples: `./manage check`, `./manage migrate`, `./manage test`.

open in web browser: http://localhost

Create migrations after doing changes at the data models:

    docker compose exec app python manage.py makemigrations

Changes to the database:

    docker compose exec app python manage.py shell
    >> from {app_name}.models import {model_name}
    >> {model_name}.objects.all().delete()

Update requirements.txt:

    pip-compile requirements.in


### Testing
Run the unit tests.
    docker compose exec app python manage.py test
    docker compose logs

There are https-tests in the /test folder which can be run with the Visual Studio Code Extension REST Client.

### Versions
* Django: 4.2
* Python: 3
* Postgres: 16
* Bootstrap: 5.3.2
* Gunicorn: 21

### Templates and static files

All template files are in the folder /app/templates
_base.html is the base template with different blocks.
home.html can be used as an example on how to use the blocks.

Static files like css, js and images are in the folder /app/static.
Uploads are in the folder /app/media.

### Admin
The admin login can be found unter /backend.


### Translation to German
Run the following command in your project directory:

    docker compose exec app python manage.py makemessages -l de

This scans your project for strings marked for translation and creates a django.po file in the locale/de/LC_MESSAGES directory.

Open the django.po file, find your strings, and add the German translation.

    docker compose exec app python manage.py compilemessages


### Production
Collect static files as preparation.

    docker compose exec app python manage.py collectstatic

Build and push to Dockerhub.

    docker build -f Dockerfile.prod -t luftdaten/datahub:tagname --platform linux/amd64 .
    docker push luftdaten/datahub:tagname

Create docker-compose.prod.yml from example-docker-compose.prod.yml by setting the secret key. Then run:

    docker compose -f docker-compose.prod.yml up -d 

## API Documentation

Open API Standard 3.1

/api/docs
https://datahub.luftdaten.at/api/docs

## License
This project is licensed under GNU General Public License v3.0.
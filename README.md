# luftdaten-datahub

## About luftdaten-datahub
luftaten-datahub is an open source plattform build on the Django Web Framework. It is an citizen science tool to explore air quality data measured by Luftdaten.at devices and other sources.

## Documentation

### Development
Development version:

    docker compose up -d
    docker compose exec web python manage.py migrate
    docker compose exec web python manage.py createsuperuser

open in web browser: http://localhost

Create migrations after doing changes at the data models:

    docker compose exec web python manage.py makemigrations

### Testing
Run the unit tests.
    docker compose exec web python manage.py test
    docker compose logs

There are https-tests in the /test folder which can be run with the Visual Studio Code Extension REST Client.

### Versions
* Django: 4.2.11
* Python: 3.12
* Postgres: 16
* Bootstrap: 5.3.2
* Gunicorn: 21.2.0

### Templates and static files

All template files are in the folder /code/templates
_base.html is the base template with different blocks.
home.html can be used as an example on how to use the blocks.

Static files like css, js and images are in the folder /code/static.

### Admin
The admin login can be found unter /backend.

### Production
Collect static files as preparation.

    docker compose exec web python manage.py collectstatic

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
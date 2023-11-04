# luftdaten-datahub

## About luftdaten-datahub
luftaten-datahub is an open-source plattform build on the Django Web Framework. It is an citizen science too to explore air quality data measured by Luftdaten.at devices and other sources.

## Documentation

### Installation
Development version:
    docker-compose up -d
    docker-compose exec web python manage.py migrate
    docker-compose exec web python manage.py createsuperuser

open in web browser: http://127.0.0.1:8000

### Development
    docker-compose exec web python manage.py collectstatic

### Testing
    docker-compose exec web python manage.py test
    docker-compose logs

### Versions
* Django: 4.2.6
* Python: 3.8
* Postgres: 16
* Bootstrap: 5.3.2 

### Admin
The admin login can be found unter /backend.

### Production
Build and push to Dockerhub.
    docker build -f Dockerfile.prod -t luftdaten/datahub:0.1 .
    docker push luftdaten/datahub:tagname
Create docker-compose.prod.yml from example-docker-compose.prod.yml by setting the secret key. Then run:
    docker-compose -f docker-compose.prod.yml up -d 

## License
This project is licensed under GNU General Public License v3.0.
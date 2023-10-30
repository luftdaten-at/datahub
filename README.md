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

### Testing
    docker-compose exec web python manage.py test
    docker-compose logs

### Versions
* Django: 2.6
* Python: 3.8
* Postgres: 16
* Bootstrap: 5.3.2 

### Production
    docker-compose exec web python manage.py collectstatic

## License
This project is licensed under GNU General Public License v3.0.
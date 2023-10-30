# luftdaten-datahub

## About luftdaten-datahub
luftaten-datahub is an open-source plattform build on the Django Web Framework. It is an citizen science too to explore air quality data measured by Luftdaten.at devices and other sources.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

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
Django: 2.6
Python: 3
Postgres: 16
Bootstrap: 5.3.2 

### Production
 docker-compose exec web python manage.py collectstatic

## License
This project is licensed under GNU General Public License v3.0.
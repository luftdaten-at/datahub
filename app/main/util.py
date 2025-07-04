import numpy as np
import logging
from django.db import connection
from django.core.exceptions import PermissionDenied
from django.db.models import Max
from django.contrib.gis.geos import Point
from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS
from datetime import datetime, timezone
from collections import defaultdict
import pytz
import time
import pyproj

from devices.models import Device, DeviceStatus
from workshops.models import Workshop, WorkshopImage
from main.enums import SensorModel, Dimension
from api.models import Location


logger = logging.getLogger('myapp')


def get_or_create_station(station_info: dict):
    '''
    station_info dict: 
    {
        "time": "2025-01-07T11:23:23.439Z",
        "device": "string",
        "firmware": "string",
        "model": 0,
        "apikey": "123",
        "battery": {
            "voltage": 0,
            "percentage": 0
        }
        "sensor_list": [
            {
                "model_id": 1,
                "dimension_list": [1, 2, 3]
            }
        ]
    }

    creates a station_status entry with the information in station_info

    return: Device if there exists a Device where Device.id = station_info['device']
            else new device is created
    '''
    station, created = Device.objects.get_or_create(
        id = station_info['device']
    )
    if created:
        station.model = station_info['model']
        station.firmware = station_info['firmware']
        station.api_key = station_info['apikey']

    # add a new DeviceStatus
    station_status = DeviceStatus.objects.create(
        time_received = datetime.now(timezone.utc),
        device = station,
        battery_voltage = station_info.get('battery', {}).get('voltage', None),
        battery_soc = station_info.get('battery', {}).get('percentage', None),
        sensor_list = station_info.get('sensor_list', None)
    )

    # update firmware field
    station.firmware = station_info['firmware']
    station.model = station_info['model']
    
    station.save()
    station_status.save()

    return station


def room_calculate_current_values(room):
        max_time_measured_per_device = room.measurements.values('device').annotate(max_time_measured=Max('time_measured'))
        measurements = []
        for entry in max_time_measured_per_device:
            measurements.extend(room.measurements.filter(device = entry['device'], time_measured = entry['max_time_measured']).all())

        def get_current_mean(dimension):
            """
            Gibt den Durchschnittswert über alle neuesten Measurements für eine gegebene Dimension zurück.
            Wenn keine Werte vorliegen, wird None zurückgegeben.
            """
            # Für jedes Measurement sammeln wir alle Values der gesuchten Dimension
            # und bilden einen Mittelwert für dieses Measurement.
            # Anschließend bilden wir aus diesen Mittelwerten den Gesamtmittelwert.
            measurement_means = []
            for m in measurements:
                dim_values = [val.value for val in m.values.all() if val.dimension == dimension]
                if dim_values:  # Nur wenn tatsächlich Werte vorhanden sind
                    measurement_means.append(np.mean(dim_values))

            # Falls keine Werte gefunden, None zurückgeben
            if measurement_means:
                return np.mean(measurement_means)
            return None

        # Temperatur
        measurements_adjusted_temp_cube = [
            value.value 
            for m in measurements
                if m.sensor_model == SensorModel.VIRTUAL_SENSOR
                    for value in m.values.all()
                        if value.dimension == Dimension.ADJUSTED_TEMP_CUBE
        ]

        current_temperature = None
        # use ADJUSTED_TEMP_CUBE if found
        if measurements_adjusted_temp_cube:
            current_temperature = measurements_adjusted_temp_cube[0]
            temperature_color = Dimension.get_color(Dimension.ADJUSTED_TEMP_CUBE, current_temperature) if current_temperature else None
        else:
            current_temperature = get_current_mean(Dimension.TEMPERATURE)
            temperature_color = Dimension.get_color(Dimension.TEMPERATURE, current_temperature) if current_temperature else None

        # PM2.5
        current_pm2_5 = get_current_mean(Dimension.PM2_5)
        pm2_5_color = Dimension.get_color(Dimension.PM2_5, current_pm2_5) if current_pm2_5 else None

        # CO2
        current_co2 = get_current_mean(Dimension.CO2)
        co2_color = Dimension.get_color(Dimension.CO2, current_co2) if current_co2 else None

        # VOC Index
        current_tvoc = get_current_mean(Dimension.TVOC)
        tvoc_color = Dimension.get_color(Dimension.TVOC, current_tvoc) if current_tvoc else None

        return [
            current_temperature, 
            temperature_color,
            current_pm2_5, 
            pm2_5_color, 
            current_co2,
            co2_color,
            current_tvoc,
            tvoc_color
        ]

def workshop_add_image(file, workshop_id):
    '''
    returns true if the picture was added sucessfully
    '''
    workshop = Workshop.objects.filter(name = workshop_id).first()
    loc = None
    time = None

    try:
        img = Image.open(file.file)
    except UnidentifiedImageError as e:
        logger.info(e)
        return False

    exif_data = img._getexif()
    # TODO get data from exif_data
    if False and exif_data:
        # 0x9003 	DateTimeOriginal 	string 	ExifIFD 	(date/time when original image was taken)
        time = exif_data.get(0x9003)
        # 0x9011 	OffsetTimeOriginal 	string 	ExifIFD 	(time zone for DateTimeOriginal)
        offset = exif_data.get(0x9011)
        # 0x882a 	34858 	Image 	Exif.Image.TimeZoneOffset
        time_zone = exif_data.get(0x882a)
        print(time)
        print(offset)
        print(time_zone)
    else:
        # read from file name
        # expect
        # 241104145947.jpg
        try:
            # set to Vienna time zone
            time = datetime.strptime(
                file._name.split('.')[0], '%y%m%d%H%M%S'
            ).replace(tzinfo=pytz.timezone('Europe/Vienna'))
        except ValueError:
            # faild to extract time
            return

    # get location from time
    points = [(r.time, r.lat, r.lon) for r in workshop.air_quality_records.all()]
    points.sort()

    for i in range(0, len(points) - 1):
        if points[i][0] <= time < points[i + 1][0]:
            # calc point
            # a1, a2, d = geod.inv(lon, lat, lon2, lat2)
            # geod.fwd(lon, lat, a1, d / 2)
            time1, lat1, lon1 = points[i]
            time2, lat2, lon2 = points[i + 1]
            f = (time - time1).total_seconds() / (time2 - time1).total_seconds()
            geod = pyproj.Geod(ellps="WGS84")
            a1, a2, d = geod.inv(lon1, lat1, lon2, lat2)
            lon_target, lat_target, _ = geod.fwd(lon1, lat1, a1, d * f)

            location, created = Location.objects.get_or_create(
                coordinates = Point(lat_target, lon_target),
                height = None
            )
            location.save()

            WorkshopImage.objects.create(
                workshop = workshop,
                image = file,
                location = location,
                time_created = time
            )

            return True

    # Picture was not added
    return False


def get_avg_temp_per_spot(workshop_id):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT ws.id, AVG(v.value)
            FROM devices_measurement AS m
            INNER JOIN api_location l ON l.id = m.location_id
            INNER JOIN devices_values v ON v.measurement_id = m.id
            INNER JOIN workshops_workshopspot ws 
                ON ST_Within(l.coordinates, ws.area) 
                AND ws.workshop_id = m.workshop_id
            WHERE m.workshop_id = %s
              AND v.dimension = 7
            GROUP BY ws.id
        """, [workshop_id])
        d1 = cursor.fetchall()
        cursor.execute("""
            select ws.id, avg(aqr.temperature)
            from api_airqualityrecord as aqr
            inner join api_location l on l.id = aqr.location_id
            inner join workshops_workshopspot ws
                on ST_Within(l.coordinates, ws.area)
                and ws.workshop_id = aqr.workshop_id
            where aqr.workshop_id = %s
            group by ws.id;
        """, [workshop_id])
        d2 = cursor.fetchall()
        d = defaultdict(list)
        for k, v in d1: d[k].append(v)
        for k, v in d2: d[k].append(v)
        res = [(k,np.mean(v)) for k,v in d.items()]
        return res

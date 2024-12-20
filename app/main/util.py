import datetime

from api.models import Device

def get_or_create_station(station_info: dict): 
    station, created = Device.objects.get_or_create(
        id = station_info['device']
    )
    if created:
        station.device_name = station_info['device']
        station.firmware = station_info['firmware']
        station.last_update = datetime.datetime.now(datetime.timezone.utc)
        station.api_key = station_info['apikey']
        station.save()

    return station

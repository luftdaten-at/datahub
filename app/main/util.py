import datetime

from devices.models import Device, DeviceStatus

def get_or_create_station(station_info: dict): 
    station, created = Device.objects.get_or_create(
        id = station_info['device']
    )
    if created:
        station.device_name = station_info['device']
        station.firmware = station_info['firmware']
        station.last_update = datetime.datetime.now(datetime.timezone.utc)
        station.api_key = station_info['apikey']
    
    # add a new DeviceStatus
    station_status = DeviceStatus.objects.create(
        time_received = datetime.datetime.now(datetime.timezone.utc),
        device = station,
        battery_voltage = station_info['battery']['voltage'],
        battery_soc = station_info['battery']['percentage'],
    )
    
    station.save()
    station_status.save()

    return station

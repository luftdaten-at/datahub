import datetime

from devices.models import Device, DeviceStatus

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
    }

    creates a station_status entry with the information in station_info

    return: Device if there exists a Device where Device.id = station_info['device']
            else new device is created
    '''
    station, created = Device.objects.get_or_create(
        id = station_info['device']
    )
    if created:
        station.device_name = station_info['device']
        station.firmware = station_info['firmware']
        station.last_update = datetime.datetime.now(datetime.timezone.utc)
        station.api_key = station_info['apikey']
        station.model = station_info['model']
        station.firmware = station_info['firmware']
    
    # add a new DeviceStatus
    station_status = DeviceStatus.objects.create(
        time_received = datetime.datetime.now(datetime.timezone.utc),
        device = station,
        battery_voltage = station_info['battery']['voltage'],
        battery_soc = station_info['battery']['percentage'],
    )

    # update firmware field
    station.firmware = station_info['firmware']
    
    station.save()
    station_status.save()

    return station

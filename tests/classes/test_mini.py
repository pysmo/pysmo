import numpy as np
from datetime import datetime, timedelta
from pysmo import (
    Seismogram,
    Station,
    Hypocenter,
    MiniSeismogram,
    MiniStation,
    MiniHypocenter
)
from pysmo.lib.defaults import SEISMOGRAM_DEFAULTS


def test_MiniSeismogram() -> None:

    my_seismogram = MiniSeismogram()

    # Check if it matches the Seismogram protocol
    assert isinstance(my_seismogram, Seismogram)

    # Check defaults
    assert my_seismogram.begin_time.year == SEISMOGRAM_DEFAULTS.begin_time.year == 1970
    assert my_seismogram.begin_time.month == SEISMOGRAM_DEFAULTS.begin_time.month == 1
    assert my_seismogram.begin_time.day == SEISMOGRAM_DEFAULTS.begin_time.day == 1
    assert my_seismogram.begin_time.hour == SEISMOGRAM_DEFAULTS.begin_time.hour == 0
    assert my_seismogram.begin_time.minute == SEISMOGRAM_DEFAULTS.begin_time.minute == 0
    assert my_seismogram.begin_time.second == SEISMOGRAM_DEFAULTS.begin_time.second == 0
    assert my_seismogram.begin_time.microsecond == SEISMOGRAM_DEFAULTS.begin_time.microsecond == 0
    assert my_seismogram.sampling_rate == SEISMOGRAM_DEFAULTS.sampling_rate == 1
    assert my_seismogram.data.size == 0
    assert len(my_seismogram) == 0
    assert my_seismogram.id is None

    # Change data
    random_data = np.random.rand(1000)
    new_time = datetime.fromisoformat('2011-11-04T00:05:23.123')
    my_seismogram.data = random_data
    assert my_seismogram.data.all() == random_data.all()
    assert my_seismogram.end_time - my_seismogram.begin_time == timedelta(
        seconds=my_seismogram.sampling_rate * (len(my_seismogram)-1))
    my_seismogram.begin_time = new_time
    assert my_seismogram.begin_time == new_time
    assert my_seismogram.end_time - my_seismogram.begin_time == timedelta(
        seconds=my_seismogram.sampling_rate * (len(my_seismogram)-1))
    my_seismogram.sampling_rate = 0.1
    assert my_seismogram.sampling_rate == 0.1
    assert my_seismogram.end_time - my_seismogram.begin_time == timedelta(
        seconds=my_seismogram.sampling_rate * (len(my_seismogram)-1))
    my_seismogram.id = 'test'
    assert my_seismogram.id == 'test'


def test_MiniStation() -> None:

    name, network, latitude, longitude = 'test', 'test', 1.1, 2.2
    new_name, new_network, new_latitude, new_longitude, new_elevation = 'foo', 'bar', 5.1, -2.2, 11

    my_station = MiniStation(name=name, network=network, latitude=latitude, longitude=longitude)

    assert isinstance(my_station, Station)

    assert my_station.name == name
    assert my_station.network == network
    assert my_station.latitude == latitude
    assert my_station.longitude == longitude
    assert my_station.elevation is None

    my_station.name = new_name
    assert my_station.name == new_name
    my_station.network = new_network
    assert my_station.network == new_network
    my_station.latitude = new_latitude
    assert my_station.latitude == new_latitude
    my_station.longitude = new_longitude
    assert my_station.longitude == new_longitude
    my_station.elevation = new_elevation
    assert my_station.elevation == new_elevation


def test_MiniHypocenter() -> None:

    latitude, longitude, depth = 1.1, 2.2, 1000
    new_latitude, new_longitude, new_depth = -21.1, -22.2, 500.2

    my_hypcenter = MiniHypocenter(latitude=latitude, longitude=longitude, depth=depth)

    assert isinstance(my_hypcenter, Hypocenter)

    assert my_hypcenter.depth == depth
    assert my_hypcenter.latitude == latitude
    assert my_hypcenter.longitude == longitude

    my_hypcenter.depth = new_depth
    assert my_hypcenter.depth == new_depth
    my_hypcenter.latitude = new_latitude
    assert my_hypcenter.latitude == new_latitude
    my_hypcenter.longitude = new_longitude
    assert my_hypcenter.longitude == new_longitude

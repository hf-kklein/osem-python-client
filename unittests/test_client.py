from datetime import datetime
from typing import AsyncGenerator

import pytest
import pytz
from aioresponses import aioresponses

from osemclient.client import OpenSenseMapClient

from .example_payloads.measurements import (
    measurements_621f53cdb527de001b06ad68_2023_12_15,
    measurements_621f53cdb527de001b06ad69_2023_12_15,
)
from .example_payloads.single_box import single_box_621f53cdb527de001b06ad5e

_berlin = pytz.timezone("Europe/Berlin")


@pytest.fixture()
async def client() -> AsyncGenerator[OpenSenseMapClient, None]:
    """
    provides a client instance
    """
    client = OpenSenseMapClient()
    yield client
    await client.close_session()


class TestClient:
    """
    tests the client features
    """

    async def test_get_sensebox(self, client: OpenSenseMapClient):
        with aioresponses() as mocked_api:
            mocked_api.get(
                "https://api.opensensemap.org/boxes/621f53cdb527de001b06ad5e",
                status=200,
                payload=single_box_621f53cdb527de001b06ad5e,
            )
            sensebox = await client.get_sensebox("621f53cdb527de001b06ad5e")
            assert sensebox.id == "621f53cdb527de001b06ad5e"
            assert len(sensebox.sensors) == 11
            assert sensebox.current_location.coordinate is not None

    async def test_get_sensor_measurements(self, client: OpenSenseMapClient):
        with aioresponses() as mocked_api:
            mocked_api.get(
                # pylint:disable=line-too-long
                "https://api.opensensemap.org/boxes/621f53cdb527de001b06ad5e/data/621f53cdb527de001b06ad69?format=json&from-date=2023-12-15T08:00:00.000000Z&to-date=2023-12-15T08:05:00.000000Z",
                status=200,
                payload=measurements_621f53cdb527de001b06ad69_2023_12_15,
            )
            measurements = await client.get_sensor_measurements(
                "621f53cdb527de001b06ad5e",
                "621f53cdb527de001b06ad69",
                from_date=_berlin.localize(datetime(2023, 12, 15, 9, 0, 0, 0)),
                to_date=_berlin.localize(datetime(2023, 12, 15, 9, 5, 0, 0)),
            )
            assert len(measurements) == 5

    async def test_get_measurements_with_sensor_metadata(self, client: OpenSenseMapClient):
        with aioresponses() as mocked_api:
            mocked_api.get(
                "https://api.opensensemap.org/boxes/621f53cdb527de001b06ad5e",
                status=200,
                payload={
                    "_id": "621f53cdb527de001b06ad5e",
                    "createdAt": "2022-03-02T11:23:57.505Z",
                    "updatedAt": "2023-12-18T13:06:48.041Z",
                    "name": "CampusJahnallee",
                    "currentLocation": {
                        "timestamp": "2022-03-02T11:23:57.500Z",
                        "coordinates": [12.353332, 51.340222],
                        "type": "Point",
                    },
                    "exposure": "outdoor",
                    "sensors": [
                        {
                            "title": "Temperatur",
                            "unit": "°C",
                            "sensorType": "HDC1080",
                            "icon": "osem-thermometer",
                            "_id": "621f53cdb527de001b06ad69",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "9.65"},
                        },
                        {
                            "title": "rel. Luftfeuchte",
                            "unit": "%",
                            "sensorType": "HDC1080",
                            "icon": "osem-humidity",
                            "_id": "621f53cdb527de001b06ad68",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "74.66"},
                        },
                        # other sensors omitted for brevity
                    ],
                    "model": "homeV2EthernetFeinstaub",
                    "lastMeasurementAt": "2023-12-18T13:06:48.018Z",
                    "description": "SenseBox der GSD Sachunterricht unter besonderer Berücksichtigung von ...",
                    "image": "621f53cdb527de001b06ad5e_rrlwm9.jpg",
                    "weblink": "https://www.erzwiss.uni-leipzig.de/institut-fuer-paedagogik-und-didaktik-im-...",
                    "loc": [
                        {
                            "geometry": {
                                "timestamp": "2022-03-02T11:23:57.500Z",
                                "coordinates": [12.353332, 51.340222],
                                "type": "Point",
                            },
                            "type": "Feature",
                        }
                    ],
                },
            )
            mocked_api.get(
                # pylint:disable=line-too-long
                "https://api.opensensemap.org/boxes/621f53cdb527de001b06ad5e/data/621f53cdb527de001b06ad69?format=json&from-date=2023-12-15T08:00:00.000000Z&to-date=2023-12-15T08:05:00.000000Z",
                status=200,
                payload=measurements_621f53cdb527de001b06ad69_2023_12_15,
            )
            mocked_api.get(
                # pylint:disable=line-too-long
                "https://api.opensensemap.org/boxes/621f53cdb527de001b06ad5e/data/621f53cdb527de001b06ad68?format=json&from-date=2023-12-15T08:00:00.000000Z&to-date=2023-12-15T08:05:00.000000Z",
                status=200,
                payload=measurements_621f53cdb527de001b06ad68_2023_12_15,
            )
            results = await client.get_measurements_with_sensor_metadata(
                "621f53cdb527de001b06ad5e",
                from_date=_berlin.localize(datetime(2023, 12, 15, 9, 0, 0, 0)),
                to_date=_berlin.localize(datetime(2023, 12, 15, 9, 5, 0, 0)),
            )
            assert len(results) == 10
            # assert the correct sensors are associated with their respective data
            assert all(3 > float(x.value) > 2 for x in results if x.unit == "°C")
            assert all(100 > float(x.value) > 99 for x in results if x.unit == "%")
            assert all(x.sensor_id == x.id for x in results)
            assert all(x.sensebox_id == "621f53cdb527de001b06ad5e" for x in results)

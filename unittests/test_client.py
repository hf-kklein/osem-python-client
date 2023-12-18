from datetime import datetime

import pytz
from aioresponses import aioresponses

from osemclient.client import OpenSenseMapClient

_berlin = pytz.timezone("Europe/Berlin")


class TestClient:
    """
    tests the client features
    """

    async def test_get_sensebox(self):
        with aioresponses() as mocked_api:
            mocked_api.get(
                "https://api.opensensemap.org/621f53cdb527de001b06ad5e",
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
                        {
                            "title": "Luftdruck",
                            "unit": "hPa",
                            "sensorType": "BMP280",
                            "icon": "osem-barometer",
                            "_id": "621f53cdb527de001b06ad67",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "1015.94"},
                        },
                        {
                            "title": "Beleuchtungsstärke",
                            "unit": "lx",
                            "sensorType": "TSL45315",
                            "icon": "osem-brightness",
                            "_id": "621f53cdb527de001b06ad66",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "3228.00"},
                        },
                        {
                            "title": "UV-Intensität",
                            "unit": "μW/cm²",
                            "sensorType": "VEML6070",
                            "icon": "osem-brightness",
                            "_id": "621f53cdb527de001b06ad65",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "118.12"},
                        },
                        {
                            "title": "PM10",
                            "unit": "µg/m³",
                            "sensorType": "SDS 011",
                            "icon": "osem-cloud",
                            "_id": "621f53cdb527de001b06ad64",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "0.20"},
                        },
                        {
                            "title": "PM2.5",
                            "unit": "µg/m³",
                            "sensorType": "SDS 011",
                            "icon": "osem-cloud",
                            "_id": "621f53cdb527de001b06ad63",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "0.20"},
                        },
                        {
                            "title": "Bodenfeuchte",
                            "unit": "%",
                            "sensorType": "SMT50",
                            "icon": "osem-thermometer",
                            "_id": "621f53cdb527de001b06ad62",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "19.71"},
                        },
                        {
                            "title": "Bodentemperatur",
                            "unit": "°C",
                            "sensorType": "SMT50",
                            "icon": "osem-thermometer",
                            "_id": "621f53cdb527de001b06ad61",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "68.27"},
                        },
                        {
                            "title": "Lautstärke",
                            "unit": "dB (A)",
                            "sensorType": "SOUNDLEVELMETER",
                            "icon": "osem-thermometer",
                            "_id": "621f53cdb527de001b06ad60",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "59.29"},
                        },
                        {
                            "title": "CO₂",
                            "unit": "ppm",
                            "sensorType": "SCD30",
                            "icon": "osem-co2",
                            "_id": "621f53cdb527de001b06ad5f",
                            "lastMeasurement": {"createdAt": "2023-12-18T13:06:48.018Z", "value": "61"},
                        },
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

            client = OpenSenseMapClient()
            sensebox = await client.get_sensebox("621f53cdb527de001b06ad5e")
            assert sensebox.id == "621f53cdb527de001b06ad5e"
            assert len(sensebox.sensors) == 11

    async def test_get_data_from_sensor(self):
        with aioresponses() as mocked_api:
            mocked_api.get(
                # pylint:disable=line-too-long
                "https://api.opensensemap.org/621f53cdb527de001b06ad5e/data/621f53cdb527de001b06ad69?format=json&from-date=2023-12-15T08-00-00.000000Z&to-date=2023-12-15T08-05-00.000000Z",
                status=200,
                payload=[
                    {"location": [12.353332, 51.340222], "createdAt": "2023-12-15T08:04:42.215Z", "value": "2.63"},
                    {"location": [12.353332, 51.340222], "createdAt": "2023-12-15T08:03:40.855Z", "value": "2.61"},
                    {"location": [12.353332, 51.340222], "createdAt": "2023-12-15T08:02:39.403Z", "value": "2.61"},
                    {"location": [12.353332, 51.340222], "createdAt": "2023-12-15T08:01:37.957Z", "value": "2.63"},
                    {"location": [12.353332, 51.340222], "createdAt": "2023-12-15T08:00:36.615Z", "value": "2.68"},
                ],
            )

            client = OpenSenseMapClient()
            measurements = await client.get_measurements(
                "621f53cdb527de001b06ad5e",
                "621f53cdb527de001b06ad69",
                from_date=_berlin.localize(datetime(2023, 12, 15, 9, 0, 0, 0)),
                to_date=_berlin.localize(datetime(2023, 12, 15, 9, 5, 0, 0)),
            )
            assert len(measurements) == 5

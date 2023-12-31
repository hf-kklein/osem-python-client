from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Optional

import pytest
import pytz
from aioresponses import aioresponses
from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude

from osemclient.client import OpenSenseMapClient
from osemclient.filtercriteria import BoundingBox, SensorFilterCriteria
from osemclient.models import Box, _Boxes, _Measurements

from .example_payloads.leipzig_boxes import leipzig_boxes
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
            assert sensebox.current_location.latitude == 51.340222
            assert sensebox.current_location.longitude == 12.353332

    async def test_get_senseboxes(self, client: OpenSenseMapClient):
        with aioresponses() as mocked_api:
            mocked_api.get(
                "https://api.opensensemap.org/boxes?bbox=12.2749644,51.3152163,12.4925729,51.3794023&full=true",
                status=200,
                payload=leipzig_boxes,
            )
            senseboxes = await client.get_senseboxes_from_area(
                BoundingBox(
                    southwest=Coordinate(longitude=Longitude(12.2749644), latitude=Latitude(51.3152163)),
                    northeast=Coordinate(longitude=Longitude(12.4925729), latitude=Latitude(51.3794023)),
                ),
            )
            assert any(senseboxes)

    async def test_get_sensor_measurements(self, client: OpenSenseMapClient):
        with aioresponses() as mocked_api:
            mocked_api.get(
                # pylint:disable=line-too-long
                "https://api.opensensemap.org/boxes/621f53cdb527de001b06ad5e/data/621f53cdb527de001b06ad69?format=json&from-date=2023-12-15T08:00:00.000000Z&to-date=2023-12-15T08:05:00.000000Z",
                status=200,
                payload=measurements_621f53cdb527de001b06ad69_2023_12_15,
            )
            measurements = [
                x
                async for x in client.get_sensor_measurements(
                    "621f53cdb527de001b06ad5e",
                    "621f53cdb527de001b06ad69",
                    from_date=_berlin.localize(datetime(2023, 12, 15, 9, 0, 0, 0)),
                    to_date=_berlin.localize(datetime(2023, 12, 15, 9, 5, 0, 0)),
                )
            ]
            assert len(measurements) == 5

    async def test_get_sensor_measurements_across_multiple_days(self, client: OpenSenseMapClient):
        total_count_of_measurements = len(measurements_621f53cdb527de001b06ad69_2023_12_15)
        with aioresponses() as mocked_api:
            mocked_api.get(
                # pylint:disable=line-too-long
                "https://api.opensensemap.org/boxes/621f53cdb527de001b06ad5e/data/621f53cdb527de001b06ad69?format=json&from-date=2023-12-15T08:00:00.000000Z&to-date=2023-12-16T08:00:00.000000Z",
                status=200,
                payload=measurements_621f53cdb527de001b06ad69_2023_12_15[0:2],
            )
            mocked_api.get(
                # pylint:disable=line-too-long
                "https://api.opensensemap.org/boxes/621f53cdb527de001b06ad5e/data/621f53cdb527de001b06ad69?format=json&from-date=2023-12-16T08:00:00.000000Z&to-date=2023-12-16T08:05:00.000000Z",
                status=200,
                payload=measurements_621f53cdb527de001b06ad69_2023_12_15[2:total_count_of_measurements],
            )
            measurements = [
                x
                async for x in client.get_sensor_measurements(
                    "621f53cdb527de001b06ad5e",
                    "621f53cdb527de001b06ad69",
                    from_date=_berlin.localize(datetime(2023, 12, 15, 9, 0, 0, 0)),
                    to_date=_berlin.localize(datetime(2023, 12, 16, 9, 5, 0, 0)),
                )
            ]
            assert len(measurements) == total_count_of_measurements

    @pytest.mark.parametrize(
        "filter_criteria,expected_num_entries",
        [
            pytest.param(None, 10),
            pytest.param(SensorFilterCriteria(), 10),
            pytest.param(SensorFilterCriteria(allowed_units={"°C"}, allowed_phenomena={"Temperatur"}), 5),
            pytest.param(SensorFilterCriteria(allowed_units={"°C"}, allowed_phenomena=None), 5),
            pytest.param(SensorFilterCriteria(allowed_units=None, allowed_phenomena={"Temperatur"}), 5),
            pytest.param(SensorFilterCriteria(allowed_units={"°F"}, allowed_phenomena={"Temperatur"}), 0),
            pytest.param(SensorFilterCriteria(allowed_units={"°C"}, allowed_phenomena={"Luftdruck"}), 0),
        ],
    )
    async def test_get_sensor_measurements_with_filter(
        self,
        client: OpenSenseMapClient,
        filter_criteria: Optional[SensorFilterCriteria],
        expected_num_entries: int,
    ):
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
            results = [
                x
                async for x in client.get_measurements_with_sensor_metadata(
                    "621f53cdb527de001b06ad5e",
                    from_date=_berlin.localize(datetime(2023, 12, 15, 9, 0, 0, 0)),
                    to_date=_berlin.localize(datetime(2023, 12, 15, 9, 5, 0, 0)),
                    sensor_filter_criteria=filter_criteria,
                )
            ]
            assert len(results) == expected_num_entries
            # assert the correct sensors are associated with their respective data
            assert all(3 > float(x.value) > 2 for x in results if x.unit == "°C")
            assert all(100 > float(x.value) > 99 for x in results if x.unit == "%")
            assert all(x.sensor_id == x.id for x in results)
            assert all(x.sensebox_id == "621f53cdb527de001b06ad5e" for x in results)

    async def test_get_measurements_from_area(self, client):
        # we monkey patch the two underlying client methods which have their own separate tests
        # this saves us from having to mock the API with aioresponses twice

        boxes_in_leipzig = _Boxes.model_validate(leipzig_boxes).root

        async def return_leipzig_boxes(_):
            return boxes_in_leipzig

        box_ids_in_area = {b.id for b in boxes_in_leipzig}
        client.get_senseboxes_from_area = return_leipzig_boxes

        _bounding_box = BoundingBox(
            southwest=Coordinate(longitude=Longitude(12.2749644), latitude=Latitude(51.3152163)),
            northeast=Coordinate(longitude=Longitude(12.4925729), latitude=Latitude(51.3794023)),
        )
        example_box = Box.model_validate(single_box_621f53cdb527de001b06ad5e)

        async def return_example_box(sensebox_id):  # pylint:disable=unused-argument
            return example_box

        client.get_sensebox = return_example_box
        _from_date = datetime.utcnow().replace(tzinfo=timezone.utc)
        _to_date = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(hours=1)
        _sensor_filter_criteria = SensorFilterCriteria()  # allowed_units={"°C"})
        example_measurements = _Measurements.model_validate(measurements_621f53cdb527de001b06ad69_2023_12_15).root

        async def return_measurements(  # pylint:disable=unused-argument
            sensebox_id: str, sensor_id: str, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
        ):
            # we only assert that the args passed to this client function (tested elsewhere) are consistent with those
            # which we to the function under test
            assert from_date == _from_date
            assert to_date == _to_date
            assert (sensebox_id == example_box.id) or (sensebox_id in box_ids_in_area)
            for m in example_measurements:
                yield m

        client.get_sensor_measurements = return_measurements
        results = [
            x
            async for x in client.get_measurements_from_area(
                from_date=_from_date,
                to_date=_to_date,
                bounding_box=_bounding_box,
                sensor_filter_criteria=_sensor_filter_criteria,
            )
        ]
        assert len(results) == len(boxes_in_leipzig) * len(example_measurements) * len(example_box.sensors)
        assert all(x.unit is not None for x in results)

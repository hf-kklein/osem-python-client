"""
contains the OpenSenseMap client; the core of this library
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Optional

from aiohttp import ClientSession, TCPConnector
from pydantic_extra_types.coordinate import Coordinate
from yarl import URL

from osemclient.filtercriteria import SensorFilterCriteria
from osemclient.models import Box, Measurement, MeasurementWithSensorMetadata, _Boxes, _Measurements

_logger = logging.getLogger(__name__)

_BASE_URL = URL("https://api.opensensemap.org/")


def _to_osem_dateformat(dt: datetime) -> str:
    # OSeM needs the post-decimal places in the ISO/RFC3339 format
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class OpenSenseMapClient:
    """
    An async HTTP client for OpenSenseMap REST API
    """

    def __init__(self, limit_per_host: int = 10):
        """
        initializes the client and its session
        """
        self._connector = TCPConnector(limit_per_host=limit_per_host)
        self._session = ClientSession(connector=self._connector, raise_for_status=True)
        _logger.info("Initialized aiohttp session")

    async def get_sensebox(self, sensebox_id: str) -> Box:
        """
        retrieves single sensebox metadata
        """
        url = _BASE_URL / "boxes" / sensebox_id
        async with self._session.get(url) as response:
            result = Box(**await response.json())
            _logger.debug("Retrieved sensebox %s", sensebox_id)
            return result

    async def get_senseboxes(self, southwest: Coordinate, northeast: Coordinate) -> list[Box]:
        """
        retrieves metadata of all senseboxes in the rectangle defined by southwest and northeast
        """
        query_params = {
            # bbox is short for "bounding box"
            "bbox": f"{southwest.longitude},{southwest.latitude},{northeast.longitude},{northeast.latitude}",
            "full": "true",
        }
        url = _BASE_URL / "boxes" % query_params
        _logger.info("Downloading all boxes between %s and %s", southwest, northeast)
        async with self._session.get(url) as response:
            result = _Boxes.model_validate(await response.json())
            _logger.debug("Retrieved %d senseboxes", len(result.root))
            return result.root

    async def get_sensor_measurements(
        self, sensebox_id: str, sensor_id: str, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> list[Measurement]:
        """
        retrieve measurements for the given box and sensor id
        """
        url = _BASE_URL / "boxes" / sensebox_id / "data" / sensor_id
        query_params: dict[str, str] = {"format": "json"}
        if from_date is not None:
            if from_date.tzinfo is None:
                raise ValueError("from_date, if set, must not be naive")
            query_params["from-date"] = _to_osem_dateformat(from_date)
        if to_date is not None:
            if to_date.tzinfo is None:
                raise ValueError("to_date, if set, must not be naive")
            query_params["to-date"] = _to_osem_dateformat(to_date)
        url = url % query_params
        async with self._session.get(url) as response:
            results = _Measurements.model_validate(await response.json())
            _logger.debug(
                "Retrieved %i measurements for box %s and sensor %s", len(results.root), sensebox_id, sensor_id
            )
            return results.root

    async def get_measurements_with_sensor_metadata(
        self,
        sensebox_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sensor_filter_criteria: Optional[SensorFilterCriteria] = None,
    ) -> list[MeasurementWithSensorMetadata]:
        """
        Returns all the box measurements in the given time range (or the APIs default if not specified).
        Other than the get_sensor_measurements method, to use this method you don't have to specify the sensor id.
        Also, the return values are annotated with the phenomenon measured.
        You can also specify a list of allowed units and phenomena to filter the results.
        The result is not sorted in a specific way.
        """
        sensor_filter: SensorFilterCriteria = sensor_filter_criteria or SensorFilterCriteria()
        box = await self.get_sensebox(sensebox_id=sensebox_id)
        sensor_tasks: list[Awaitable[list[Measurement]]] = [
            self.get_sensor_measurements(box.id, sensor.id, from_date=from_date, to_date=to_date)
            for sensor in box.sensors
        ]
        sensor_measurements = await asyncio.gather(*sensor_tasks)
        _logger.debug("Retrieved %i measurement series for sensors of box %s", len(sensor_measurements), sensebox_id)
        results = [
            MeasurementWithSensorMetadata.model_validate(
                {**sensor.dict(by_alias=True), **measurement.dict(by_alias=True), "senseboxId": box.id}
            )
            for sensor, sensor_measurement_list in zip(box.sensors, sensor_measurements)
            for measurement in sensor_measurement_list
            if (sensor_filter.allowed_units is None or sensor.unit in sensor_filter.allowed_units)
            and (sensor_filter.allowed_phenomena is None or sensor.title in sensor_filter.allowed_phenomena)
        ]
        return results

    async def close_session(self):
        """
        closes the client session
        """
        if self._session is not None and not self._session.closed:
            _logger.info("Closing aiohttp session")
            await self._session.close()
            self._session = None

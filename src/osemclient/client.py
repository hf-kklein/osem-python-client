"""
contains the OpenSenseMap client; the core of this library
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Generator, Optional

from aiohttp import ClientSession, TCPConnector
from aiostream import pipe, stream
from yarl import URL

from osemclient.filtercriteria import BoundingBox, SensorFilterCriteria
from osemclient.models import Box, Measurement, MeasurementWithSensorMetadata, SensorMetadata, _Boxes, _Measurements

_logger = logging.getLogger(__name__)

_BASE_URL = URL("https://api.opensensemap.org/")

_DEFAULT_WIDTH = timedelta(days=1)


def _to_osem_dateformat(dt: datetime) -> str:
    # OSeM needs the post-decimal places in the ISO/RFC3339 format
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _get_start_end_slices(
    from_date: datetime, to_date: datetime, width: timedelta
) -> Generator[tuple[datetime, datetime], None, None]:
    """
    yields tuples of start and end dates, where each tuple represents a time slice of max width `width`.
    The first and last slice will be smaller than `width` if `from_date` or `to_date` are not a multiple of `width`.
    """
    current_start = from_date
    while current_start < to_date:
        current_end = min(current_start + width, to_date)
        yield current_start, current_end
        current_start = current_end


def _get_urls_in_date_range(
    from_date: datetime, to_date: datetime, width: timedelta, sensebox_id: str, sensor_id: str
) -> Generator[URL, None, None]:
    url = _BASE_URL / "boxes" / sensebox_id / "data" / sensor_id
    query_params: dict[str, str] = {"format": "json"}
    for start_date, end_date in _get_start_end_slices(from_date=from_date, to_date=to_date, width=width):
        query_params["from-date"] = _to_osem_dateformat(start_date)
        query_params["to-date"] = _to_osem_dateformat(end_date)
        yield url % query_params


async def _get_sensor_measurements_with_sensor_metadata(
    box: Box, sensor: SensorMetadata, meas_gen: AsyncGenerator[Measurement, None]
) -> AsyncGenerator[MeasurementWithSensorMetadata, None]:
    # just a wrapper around another generator, to add the box and sensor metadata
    async for measurement in meas_gen:
        yield MeasurementWithSensorMetadata.model_validate(
            {**sensor.model_dump(by_alias=True), **measurement.model_dump(by_alias=True), "senseboxId": box.id}
        )


class OpenSenseMapClient:
    """
    An async HTTP client for OpenSenseMap REST API
    """

    def __init__(self, limit_per_host: int = 10, number_of_concurrent_requests: int = 100):
        """
        initializes the client and its session.
        The limit_per_host is a limit for the number of concurrent connections to the same host (aiohttp internal).
        The number_of_concurrent_requests is the number of concurrent requests which this client sends to the OSeM API.
        Change limit_per_host if the response time/internet connection is too slow.
        Change number_of_concurrent_requests if you run into aiohttp timeouts because the pending requests cannot be
        processed fast enough.
        """
        self._connector = TCPConnector(limit_per_host=limit_per_host)
        self._session = ClientSession(connector=self._connector, raise_for_status=True)
        self._number_of_concurrent_requests = number_of_concurrent_requests  # started at once
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

    async def get_senseboxes_from_area(self, bounding_box: BoundingBox) -> list[Box]:
        """
        retrieves metadata of all senseboxes in the rectangle defined by southwest and northeast
        """
        query_params = {
            # bbox is short for "bounding box"
            # pylint:disable=line-too-long
            "bbox": f"{bounding_box.southwest.longitude},{bounding_box.southwest.latitude},{bounding_box.northeast.longitude},{bounding_box.northeast.latitude}",
            "full": "true",
        }
        url = _BASE_URL / "boxes" % query_params
        _logger.info("Downloading all boxes between %s and %s", bounding_box.southwest, bounding_box.northeast)
        async with self._session.get(url) as response:
            result = _Boxes.model_validate(await response.json())
            _logger.debug("Retrieved %d senseboxes", len(result.root))
            return result.root

    async def _perform_measurements_request(self, url: URL) -> AsyncGenerator[list[Measurement], None]:
        _logger.debug("Starting download of measurements from %s", url)
        try:
            async with self._session.get(url) as response:
                result = _Measurements.model_validate(await response.json())
                _logger.debug("Retrieved %d measurements", len(result.root))
                yield result.root
        finally:
            _logger.debug("Finished downloading measurements from %s", url)

    async def get_sensor_measurements(
        self, sensebox_id: str, sensor_id: str, from_date: Optional[datetime] = None, to_date: Optional[datetime] = None
    ) -> AsyncGenerator[Measurement, None]:
        """
        retrieve measurements for the given box and sensor id
        """
        if from_date is not None:
            if from_date.tzinfo is None:
                raise ValueError("from_date, if set, must not be naive")
        if to_date is not None:
            if to_date.tzinfo is None:
                raise ValueError("to_date, if set, must not be naive")
        _from_date: datetime
        _to_date: datetime
        # We could build the following logic with less verbose if/elif/else clauses, but this way it's easier to
        # understand and especially easier to understand for the type checker.
        if from_date is None and to_date is None:
            _to_date = datetime.utcnow().replace(tzinfo=timezone.utc)
            _from_date = _to_date - _DEFAULT_WIDTH
        elif from_date is None and to_date is not None:
            _from_date = to_date - _DEFAULT_WIDTH
            _to_date = to_date
        elif to_date is None and from_date is not None:
            _from_date = from_date
            _to_date = from_date + _DEFAULT_WIDTH
        elif from_date is not None and to_date is not None:
            _from_date = from_date
            _to_date = to_date
        del from_date  # just to prevent accidental use
        del to_date
        # The OSeM API only allows retrieving 10k measurements at once.
        # We could try to derive the time span width from the measurement frequency, but it's easier to just always
        # use a width of 1 day and merge the results.
        measurements_tasks = (
            self._perform_measurements_request(_url)
            for _url in _get_urls_in_date_range(
                from_date=_from_date,
                to_date=_to_date,
                width=_DEFAULT_WIDTH,
                sensebox_id=sensebox_id,
                sensor_id=sensor_id,
            )
        )
        measurements_chunks_streamer = stream.merge(*measurements_tasks) | pipe.chunks(
            self._number_of_concurrent_requests
        )  # todo: I thought you could use flatten here to unpack the chunks again but didn't get it working
        number_of_measurements_yielded = 0
        async with measurements_chunks_streamer.stream() as measurements_chunk_stream:
            async for measurements_chunks in measurements_chunk_stream:
                for measurements_chunk in measurements_chunks:
                    for measurement in measurements_chunk:
                        yield measurement
                        number_of_measurements_yielded += 1
                        if number_of_measurements_yielded % 10_000 == 0:
                            _logger.debug("Yielded %d measurements so far...", number_of_measurements_yielded)
        _logger.info(
            "Yielded %d measurements in total from box %s and sensor %s",
            number_of_measurements_yielded,
            sensebox_id,
            sensor_id,
        )

    async def get_measurements_with_sensor_metadata(
        self,
        sensebox_id: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sensor_filter_criteria: Optional[SensorFilterCriteria] = None,
    ) -> AsyncGenerator[MeasurementWithSensorMetadata, None]:
        """
        Yields all the box measurements in the given time range (or the APIs default if not specified).
        Other than the get_sensor_measurements method, to use this method you don't have to specify the sensor id.
        Also, the return values are annotated with the phenomenon measured.
        You can also specify a list of allowed units and phenomena to filter the results.
        The result is not guaranteed to be sorted in any specific way, but you'll at least see chunks of data
        originating from the same sensor.
        """
        sensor_filter: SensorFilterCriteria = sensor_filter_criteria or SensorFilterCriteria()
        box = await self.get_sensebox(sensebox_id=sensebox_id)
        mm_generators = [
            _get_sensor_measurements_with_sensor_metadata(
                box,
                sensor,
                self.get_sensor_measurements(
                    sensebox_id=sensebox_id, sensor_id=sensor.id, from_date=from_date, to_date=to_date
                ),
            )
            for sensor in box.sensors
            if sensor_filter.are_fulfilled_by(sensor)
        ]
        if not any(mm_generators):
            _logger.info("No sensors match the criteria for box '%s'", sensebox_id)
            return
        merged_metadata_measurement_generators = stream.merge(*mm_generators)
        async with merged_metadata_measurement_generators.stream() as measurements_with_metadata_stream:
            async for measurement_with_metadata in measurements_with_metadata_stream:
                yield measurement_with_metadata

    async def get_measurements_from_area(
        self,
        bounding_box: BoundingBox,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        sensor_filter_criteria: Optional[SensorFilterCriteria] = None,
    ) -> AsyncGenerator[MeasurementWithSensorMetadata, None]:
        """
        Yields all the box measurements in the given time range (or the APIs default if not specified).
        Other than the get_sensor_measurements method, to use this method you don't have to specify the sensor id.
        Also, the return values are annotated with the phenomenon measured.
        You can also specify a list of allowed units and phenomena to filter the results.
        The result is not guaranteed to be sorted in any specific way, but you'll at least see chunks of data
        originating from the same sensor.
        """
        boxes = await self.get_senseboxes_from_area(bounding_box)
        measurements_from_boxes_generators = (
            self.get_measurements_with_sensor_metadata(
                from_date=from_date, to_date=to_date, sensor_filter_criteria=sensor_filter_criteria, sensebox_id=box.id
            )
            for box in boxes
        )
        distinct_box_ids_in_yielded_data: set[str] = set()
        merged_mmfb_generators = stream.merge(*measurements_from_boxes_generators)
        async with merged_mmfb_generators.stream() as mmfb_stream:
            async for measurement_with_metadata in mmfb_stream:
                yield measurement_with_metadata
                distinct_box_ids_in_yielded_data.add(measurement_with_metadata.sensebox_id)
        _logger.info("Yielded measurements from %d boxes in total", len(distinct_box_ids_in_yielded_data))

    async def close_session(self):
        """
        closes the client session
        """
        if self._session is not None and not self._session.closed:
            _logger.info("Closing aiohttp session")
            await self._session.close()
            self._session = None

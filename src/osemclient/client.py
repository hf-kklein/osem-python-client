"""
This a docstring for the module.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from aiohttp import ClientSession, TCPConnector
from yarl import URL

from osemclient.models import Box, Measurement, _Measurements

_logger = logging.getLogger(__name__)

_BASE_URL = URL("https://api.opensensemap.org/")


def _to_osem_dateformat(dt: datetime) -> str:
    # OSeM needs the post-decimal places in the ISO/RFC3339 format
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S.%fZ")


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

    async def get_measurements(
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

    async def close_session(self):
        """
        closes the client session
        """
        if self._session is not None and not self._session.closed:
            _logger.info("Closing aiohttp session")
            await self._session.close()
            self._session = None

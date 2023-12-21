"""the example from the readme"""
import asyncio

from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude

from osemclient.client import OpenSenseMapClient
from osemclient.filtercriteria import BoundingBox


async def get_recent_measurements(sensebox_id: str) -> None:
    """
    downloads the latest 10_000 measurements for the given sensebox id
    """
    client = OpenSenseMapClient()
    try:
        measurements = [x async for x in client.get_measurements_with_sensor_metadata(sensebox_id=sensebox_id)]
        print(
            f"There are {len(measurements)} measurements available: "
            + ", ".join(str(ms) for ms in measurements[0:3])
            + " ..."
        )
        assert any(m for m in measurements if m.unit == "°C")  # there are temperature measurements
        assert any(m for m in measurements if m.unit == "hPa")  # there are air pressure measurements
        # and many more
    finally:
        await client.close_session()


async def get_recent_measurements_in_leipzig_area() -> None:
    """
    Downloads the most recent measurements for all boxes in Leipzig, Germany (defined by its coordinates)
    """
    client = OpenSenseMapClient(limit_per_host=1000)
    try:
        measurements = [
            m
            async for m in client.get_measurements_from_area(
                BoundingBox(
                    southwest=Coordinate(latitude=Latitude(51.2763), longitude=Longitude(12.3336)),
                    northeast=Coordinate(latitude=Latitude(51.3992), longitude=Longitude(12.4306)),
                ),
            )
        ]
        print(
            f"There are {len(measurements)} measurements in the Leipzig area: "
            + ", ".join(str(ms) for ms in measurements[0:3])
            + " ..."
        )
    finally:
        await client.close_session()


if __name__ == "__main__":
    asyncio.run(get_recent_measurements_in_leipzig_area())
    asyncio.run(get_recent_measurements(sensebox_id="621f53cdb527de001b06ad5e"))

"""the example from the readme"""
import asyncio

from osemclient.client import OpenSenseMapClient


async def get_recent_measurements(sensebox_id: str):
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


if __name__ == "__main__":
    asyncio.run(get_recent_measurements(sensebox_id="621f53cdb527de001b06ad5e"))

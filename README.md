# osem-python-client
`osemclient` is an async Python client with fully typed model classes for the OpenSenseMap REST API.
It is based on aiohttp and Pydantic.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![PyPI status badge](https://img.shields.io/pypi/v/osemclient)
![Python Versions (officially) supported](https://img.shields.io/pypi/pyversions/osemclient.svg)

![Unittests status badge](https://github.com/hf-kklein/osem-python-client/workflows/Unittests/badge.svg)
![Coverage status badge](https://github.com//hf-kklein/osem-python-client/workflows/Coverage/badge.svg)
![Linting status badge](https://github.com/hf-kklein/osem-python-client/workflows/Linting/badge.svg)
![Black status badge](https://github.com/hf-kklein/osem-python-client/workflows/Formatting/badge.svg)


## Usage
```bash
pip install osemclient
```

```python
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

```
Methods that return measurement values are async generators.
This allows for kind of streaming the data from the OSeM API and avoids large bloating lists in memory.

## State of this Project
This project is **very alpha** and more a proof of concept.
It only supports two GET API endpoints as of 2023-12-18 and even those are not covered completely.
If you _really_ want to use it, there's still work to be done but this project might be a good foundation.

## Development
Check the instructions in our [Python Template Repository](https://github.com/Hochfrequenz/python_template_repository#how-to-use-this-repository-on-your-machine).
tl;dr: tox.

## Contribute
You are very welcome to contribute to this template repository by opening a pull request against the main branch.

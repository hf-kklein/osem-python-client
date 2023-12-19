# osem-python-client
`osemclient` is an async Python client for the OpenSenseMap REST API.
It is based on aiohttp and Pydantic.

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
from typing import Awaitable

from osemclient.client import OpenSenseMapClient
from osemclient.models import Measurement


async def get_recent_measurements(sensebox_id: str):
    client = OpenSenseMapClient()
    box = await client.get_sensebox(sensebox_id)
    sensor_tasks: list[Awaitable[list[Measurement]]] = [
        client.get_measurements(box.id, sensor.id) for sensor in box.sensors
    ]
    measurement_series = await asyncio.gather(*sensor_tasks)
    await client.close_session()


if __name__ == "__main__":
    asyncio.run(get_recent_measurements(sensebox_id="621f53cdb527de001b06ad5e"))

```

## State of this Project
This project is **very alpha** and more a proof of concept.
It only supports two GET API endpoints as of 2023-12-18 and even those are not covered completely.
If you _really_ want to use it, there's still work to be done but this project might be a good foundation.

## Development
Check the instructions in our [Python Template Repository](https://github.com/Hochfrequenz/python_template_repository#how-to-use-this-repository-on-your-machine).
tl;dr: tox.

## Contribute
You are very welcome to contribute to this template repository by opening a pull request against the main branch.
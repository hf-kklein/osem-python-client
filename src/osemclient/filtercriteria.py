"""
helper classes for filtering boxes and/or sensors
"""
from typing import Optional

from pydantic import BaseModel


class SensorFilterCriteria(BaseModel):
    """
    easy to use-representation of filters for sensors.
    Its default values mean "no filter is applied".
    """

    allowed_units: Optional[set[str]] = None  #: applied on sensor/unit
    allowed_phenomena: Optional[set[str]] = None  #: applied on sensor/title

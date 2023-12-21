"""
helper classes for filtering boxes and/or sensors
"""
from typing import Optional

from pydantic import BaseModel
from pydantic_extra_types.coordinate import Coordinate

from osemclient.models import SensorMetadata

# pylint:disable=too-few-public-methods


class SensorFilterCriteria(BaseModel):
    """
    easy to use-representation of filters for sensors.
    Its default values mean "no filter is applied".
    """

    allowed_units: Optional[set[str]] = None  #: applied on sensor/unit
    allowed_phenomena: Optional[set[str]] = None  #: applied on sensor/title

    def are_fulfilled_by(self, sensor: SensorMetadata) -> bool:
        """
        returns true iff the given sensor fulfills this criteria
        """
        # pylint:disable=unsupported-membership-test)
        unit_is_ok = self.allowed_units is None or sensor.unit in self.allowed_units
        phenomenon_is_ok = self.allowed_phenomena is None or sensor.title in self.allowed_phenomena
        return unit_is_ok and phenomenon_is_ok


class BoundingBox(BaseModel):
    """
    a bounding box defined by two coordinates
    """

    southwest: Coordinate
    northeast: Coordinate


class BoxFilterCriteria(BaseModel):
    """
    easy to use-representation of filters for senseboxes.
    Its default values mean "no filter is applied".
    """

    bounding_box: Optional[BoundingBox] = None

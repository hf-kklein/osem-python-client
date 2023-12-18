"""
This package contains the data models exposed by the API.
Those are handcrafted as of now, but could be generated from the OpenSenseMap API schema.
"""

from datetime import datetime

from pydantic import BaseModel, Field, RootModel


class SensorMetadata(BaseModel):
    """
    Information about a sensor (which is part of a sensebox)
    """

    id: str = Field(alias="_id")  #: unique ID of this sensor; e.g. "621f53cdb527de001b06ad69"
    title: str  #: name of the sensor (or phenomenon in German, mostly)
    unit: str  #: unit of the measurement, e.g. "°C"
    sensor_type: str = Field(alias="sensorType")  #: type of the sensor, e.g. "HDC1080"
    # there are more properties that are not relevant to us yet


class Box(BaseModel):
    """
    A sensebox is a station where sensors are installed. It has a location and multiple sensors.
    The object that is returned by https://api.opensensemap.org/boxes/:senseBoxId
    """

    id: str = Field(alias="_id")  #: unique ID of thise sensebox, e.g. "621f53cdb527de001b06ad5e"

    # there are more properties that are not relevant to us yet
    sensors: list[SensorMetadata]  #: list of sensors that are installed in this sensebox


class Measurement(BaseModel):
    """
    One measurement of a sensor at a specific point in time.
    One of the items of the array that is returned by
    https://api.opensensemap.org/boxes/:senseBoxId/data/:sensorId?from-date=fromDate&to-date=toDate
    """

    # missing location (we don't care yet)
    created_at: datetime = Field(alias="createdAt")  #: point in time when the measurement was taken
    value: str  #: the measurement value (needs to be associated with the unit from SensorMetadata); always a string


class _Measurements(RootModel[list[Measurement]]):
    """
    The array that is returned by
    https://api.opensensemap.org/boxes/:senseBoxId/data/:sensorId?from-date=fromDate&to-date=toDate
    """

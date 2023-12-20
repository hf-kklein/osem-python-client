"""
This module contains the data models exposed by the API.
Those are handcrafted as of now, but could be generated from the OpenSenseMap API schema.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, RootModel, computed_field
from pydantic_extra_types.coordinate import Coordinate, Latitude, Longitude


class Measurement(BaseModel):
    """
    One measurement of a sensor at a specific point in time.
    One of the items of the array that is returned by
    https://api.opensensemap.org/boxes/:senseBoxId/data/:sensorId?from-date=fromDate&to-date=toDate
    """

    # todo: missing location
    created_at: datetime = Field(alias="createdAt")  #: point in time when the measurement was taken
    value: str  #: the measurement value (needs to be associated with the unit from SensorMetadata); always a string


class SensorMetadata(BaseModel):
    """
    Information about a sensor (which is part of a sensebox)
    """

    id: str = Field(alias="_id")  #: unique ID of this sensor; e.g. "621f53cdb527de001b06ad69"
    title: str  #: name of the sensor (or phenomenon in German, mostly)
    unit: str  #: unit of the measurement, e.g. "°C"
    sensor_type: Optional[str] = Field(alias="sensorType", default=None)  #: type of the sensor, e.g. "HDC1080"
    # this is nullable because of https://github.com/sensebox/openSenseMap-API/issues/861
    icon: Optional[str] = None  #: the visual representation for the openSenseMap of this sensor
    last_measurement: Optional[Measurement] = Field(alias="lastMeasurement", default=None)
    """the latest measurement of one of the sensors of this senseBox"""


class Location(BaseModel):
    """
    location of a sense box
    """

    type: str  #: e.g. "Point"
    raw_coordinates: list[Decimal | int] = Field(alias="coordinates")  #: e.g. [12.45451, 51.152005]
    timestamp: datetime

    @computed_field(return_type=Longitude)
    def longitude(self):
        """
        longitude, e.g. 12.45451
        :return:
        """
        return Longitude(self.raw_coordinates[0])  # pylint:disable=unsubscriptable-object

    @computed_field(return_type=Latitude)
    def latitude(self):
        """
        latitude, e.g. 51.152005
        :return:
        """
        return Latitude(self.raw_coordinates[1])  # pylint:disable=unsubscriptable-object

    @computed_field(return_type=Coordinate)
    def coordinate(self):
        """
        coordinate in a pydantic coordinate format
        """
        return Coordinate(latitude=self.latitude, longitude=self.longitude)

    @computed_field(return_type=Optional[int])
    def altitude(self):
        """meters above sea level"""
        # todo: really?
        try:
            return self.raw_coordinates[2]  # pylint:disable=unsubscriptable-object
        except IndexError:
            return None


class Box(BaseModel):
    """
    A sensebox is a station where sensors are installed. It has a location and multiple sensors.
    The object that is returned by https://api.opensensemap.org/boxes/:senseBoxId
    """

    # see https://docs.opensensemap.org/#api-Boxes-getBox
    id: str = Field(alias="_id")  #: unique identifier of this senseBox , e.g. "621f53cdb527de001b06ad5e"
    name: str  #: name of this senseBox
    exposure: str  #: the exposure of this senseBox, e.g. "outdoor"
    model: str  #: the model of this senseBox, e.g. "homeV2WifiFeinstaub"
    last_measurement_at: Optional[datetime] = Field(
        alias="lastMeasurementAt", default=None
    )  #: timestamp of the lastest measurement of one of the sensors of this senseBox
    # nullable because of https://github.com/sensebox/openSenseMap-API/issues/862
    weblink: Optional[str] = None  #: external weblink
    description: Optional[str] = None  #: detailed description of the senseBox
    created_at: datetime = Field(alias="createdAt")  #: timestamp of the creation of the senseBox
    updated_at: datetime = Field(alias="updatedAt")  #: timestamp of the last update of the senseBox
    grouptags: Optional[list[str]] = Field(alias="grouptag", default=None)  #: the grouptags of this senseBox
    image: Optional[str] = None  #: image showing the senseBox, e.g. '60a9114b6fedc6001b9ddd1d_qtk9d7.jpg'
    sensors: list[SensorMetadata]  #: list of sensors that are installed in this sensebox
    current_location: Location = Field(alias="currentLocation")  #: location of the senseBox


class _Boxes(RootModel[list[Box]]):  # pylint:disable=too-few-public-methods
    """
    represents a list of boxes returned by the API
    """


class _Measurements(RootModel[list[Measurement]]):  # pylint:disable=too-few-public-methods
    """
    The array that is returned by
    https://api.opensensemap.org/boxes/:senseBoxId/data/:sensorId?from-date=fromDate&to-date=toDate
    """


class MeasurementWithSensorMetadata(Measurement, SensorMetadata):
    """
    A measurement with the associated sensor metadata.
    """

    sensebox_id: str = Field(alias="senseboxId")  #: ID of the sensebox to which the sensor belongs

    @computed_field(return_type=str)
    def sensor_id(self):
        """
        sensor_id is more readable than then plain (implicit) id. The latter makes sense when you only retrieve sensors,
        but together with the actual measurement data, it might be clearer to use explicit sensor_id.
        """
        return self.id

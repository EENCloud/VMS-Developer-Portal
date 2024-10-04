from pydantic import BaseModel, Field
from typing import List, Optional


class DataSchema(BaseModel):
    type: str = Field()


class ObjectDetectionData(DataSchema):
    timestamp: str
    boundingBox: list = Field(
        description=""" Array of 4 floats describing a bounding box around the object of interest. Note that the percentage defined below
  is as a decimal value between 0 and 1. This means 55% would have to be provided as 0.55.
  * First - top left corner horizontal position (from left) as a percentage of the image width.
  * Second - top left corner vertical position (from top) as a percentage of the total image height.
  * Third - bottom right corner horizontal position (from left) as a percentage of the image width.
  * Fourth - bottom right corner vertical position (from top) as a percentage of the image height.""")


class FullFrameImageData(DataSchema):
    timestamp: str
    httpsUrl: str
    feedType: str


class ObjectClassificationData(DataSchema):
    class_: str = Field(alias="class")
    confidence: float


class CreatorDetailsData(DataSchema):
    id: str
    vendor: str
    application: Optional[str] = None
    hardwareModel: Optional[str] = None
    version: Optional[str] = None
    needsValidation: Optional[bool] = None


class ObjectRegionmappingData(DataSchema):
    regions: list


class CreateEvent(BaseModel):
    startTimestamp: str
    endTimestamp: Optional[str] = None
    span: bool
    accountId: str
    actorId: str
    actorAccountId: str
    actorType: str
    actorName: Optional[str] = None
    creatorId: str
    type: str
    data: list
    dataSchemas: List[DataSchema]

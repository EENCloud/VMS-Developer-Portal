from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal, Annotated


class DataSchema(BaseModel):
    type: str = Field()


class ObjectDetectionData(DataSchema):
    type: Literal['een.objectDetection.v1']
    timestamp: str
    boundingBox: List[float] = Field(
        description=""" Array of 4 floats describing a bounding box around the object of interest. Note that the percentage defined below
  is as a decimal value between 0 and 1. This means 55% would have to be provided as 0.55.
  * First - top left corner horizontal position (from left) as a percentage of the image width.
  * Second - top left corner vertical position (from top) as a percentage of the total image height.
  * Third - bottom right corner horizontal position (from left) as a percentage of the image width.
  * Fourth - bottom right corner vertical position (from top) as a percentage of the image height.""")


class FullFrameImageData(DataSchema):
    type: Literal['een.fullFrameImageUrl.v1']
    timestamp: str
    httpsUrl: str
    feedType: str


class ObjectClassificationData(DataSchema):
    type: Literal['een.objectClassification.v1']
    class_: str = Field(alias="class")
    confidence: float

    class Config:
        populate_by_name = True


class CreatorDetailsData(DataSchema):
    type: Literal['een.creatorDetails.v1']
    id: str
    vendor: str
    application: Optional[str] = None
    hardwareModel: Optional[str] = None
    version: Optional[str] = None
    needsValidation: Optional[bool] = None


class ObjectRegionmappingData(DataSchema):
    type: Literal['een.objectRegionMapping.v1']
    regions: list


class CreateEvent(BaseModel):
    startTimestamp: str
    endTimestamp: Optional[str] = None
    span: bool
    accountId: str
    actorId: str
    actorAccountId: str
    actorType: str
    creatorId: str
    type: str
    dataSchemas: list
    data: List[Annotated[Union[
        ObjectDetectionData,
        FullFrameImageData,
        ObjectClassificationData,
        CreatorDetailsData,
        ObjectRegionmappingData], Field(discriminator='type')]]

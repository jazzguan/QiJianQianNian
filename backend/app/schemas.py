"""历史演化接口的请求与响应模型。"""

from typing import Optional

from pydantic import BaseModel, Field


class DynastyInfo(BaseModel):
    id: str
    name: str
    years: str
    intro: str
    porcelainId: str
    evolutionNote: str


class GlazeStyle(BaseModel):
    color: str
    roughness: float
    metalness: float
    clearcoat: float
    decoration: str


class PorcelainParams(BaseModel):
    height: float
    maxBellyDiameter: float
    mouthDiameter: float
    footDiameter: float


class PorcelainPart(BaseModel):
    id: str
    name: str
    yMin: float
    yMax: float
    formDescription: str
    history: str
    knowledge: str


class Porcelain(BaseModel):
    id: str
    name: str
    category: str
    dynasty: str
    dynastyName: str
    period: str
    summary: str
    description: str
    shape: list[list[float]]
    glaze: GlazeStyle
    modelUrl: Optional[str] = None
    imageUrl: Optional[str] = None
    params: PorcelainParams
    formFeatures: list[str]
    decorationFeatures: list[str]
    craftFeatures: list[str]
    history: str
    parts: list[PorcelainPart]


class TimelineResponse(BaseModel):
    dynasties: list[DynastyInfo]


class PersonalizedMatch(BaseModel):
    dynasty: str
    porcelainId: Optional[str] = None
    difference: str = ""
    emptyReason: Optional[str] = None


class PersonalizedMatchRequest(BaseModel):
    category: str = Field(min_length=1, description="上传器物的器型类别")


class PersonalizedMatchResponse(BaseModel):
    matches: list[PersonalizedMatch]

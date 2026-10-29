"""历史演化 FastAPI 路由。"""

from fastapi import APIRouter, HTTPException

from .schemas import (
    DynastyInfo,
    PersonalizedMatchRequest,
    PersonalizedMatchResponse,
    Porcelain,
    TimelineResponse,
)
from .timeline_service import (
    get_dynasty_porcelain,
    get_personalized_matches,
    get_porcelain,
    list_dynasties,
)


router = APIRouter(prefix="/api", tags=["历史演化"])


@router.get("/timeline", response_model=TimelineResponse)
def api_timeline() -> TimelineResponse:
    return TimelineResponse(
        dynasties=[DynastyInfo.parse_obj(item) for item in list_dynasties()]
    )


@router.get("/timeline/{dynasty}", response_model=Porcelain)
def api_dynasty_porcelain(dynasty: str) -> Porcelain:
    item = get_dynasty_porcelain(dynasty)
    if item is None:
        raise HTTPException(status_code=404, detail=f"未找到朝代：{dynasty}")
    return Porcelain.parse_obj(item)


@router.get("/porcelain/{porcelain_id}", response_model=Porcelain)
def api_porcelain(porcelain_id: str) -> Porcelain:
    item = get_porcelain(porcelain_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"未找到瓷器：{porcelain_id}")
    return Porcelain.parse_obj(item)


@router.post("/evolution/match", response_model=PersonalizedMatchResponse)
def api_evolution_match(payload: PersonalizedMatchRequest) -> PersonalizedMatchResponse:
    return PersonalizedMatchResponse(matches=get_personalized_matches(payload.category))

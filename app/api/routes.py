from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.schemas import SearchRequest, SearchResponse
from app.services.naver_search import search_naver_view
from app.services.sheet_checker import check_sheet_exposure

router = APIRouter()


class SheetCheckRequest(BaseModel):
    start_date: str  # 시작일 (월/일 형식: 1/1)
    end_date: str    # 종료일 (월/일 형식: 1/31)


@router.post("/check-exposure", response_model=SearchResponse)
async def check_exposure(request: SearchRequest) -> SearchResponse:
    """블로그 노출 여부 확인 API"""

    if not request.keyword.strip():
        raise HTTPException(status_code=400, detail="키워드를 입력해주세요.")

    if not request.blog_url.strip():
        raise HTTPException(status_code=400, detail="블로그 URL을 입력해주세요.")

    result = search_naver_view(request.keyword.strip(), request.blog_url.strip())

    return result


@router.post("/check-sheet")
async def check_sheet(request: SheetCheckRequest):
    """구글 시트 기간별 노출 체크 API"""

    if not request.start_date.strip() or not request.end_date.strip():
        raise HTTPException(status_code=400, detail="시작일과 종료일을 입력해주세요.")

    result = check_sheet_exposure(request.start_date.strip(), request.end_date.strip())

    return result

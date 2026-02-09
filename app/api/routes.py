from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.schemas import SearchRequest, SearchResponse
from app.services.naver_search import search_naver_view
from app.services.sheet_checker import (
    check_sheet_exposure,
    start_check_in_background,
    task_state,
)

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
    """구글 시트 기간별 노출 체크 API (백그라운드 실행)"""

    if not request.start_date.strip() or not request.end_date.strip():
        raise HTTPException(status_code=400, detail="시작일과 종료일을 입력해주세요.")

    if task_state["status"] in ("running", "paused"):
        raise HTTPException(status_code=409, detail="이미 실행 중인 작업이 있습니다.")

    start_check_in_background(request.start_date.strip(), request.end_date.strip())

    return {"success": True, "message": "노출 체크가 시작되었습니다."}


@router.get("/status")
async def get_status():
    """현재 작업 상태 반환"""
    return {
        "status": task_state["status"],
        "current": task_state["current"],
        "total": task_state["total"],
        "message": task_state["message"],
        "result": task_state["result"],
    }


@router.post("/pause")
async def toggle_pause():
    """일시정지 / 재개 토글"""
    if task_state["status"] == "running":
        task_state["status"] = "paused"
        task_state["message"] = "일시정지됨"
        return {"success": True, "status": "paused"}
    elif task_state["status"] == "paused":
        task_state["status"] = "running"
        return {"success": True, "status": "running"}
    else:
        raise HTTPException(status_code=400, detail="실행 중인 작업이 없습니다.")


@router.post("/stop")
async def stop_task():
    """작업 중단"""
    if task_state["status"] in ("running", "paused"):
        task_state["status"] = "stopped"
        return {"success": True, "message": "중단 요청됨"}
    else:
        raise HTTPException(status_code=400, detail="실행 중인 작업이 없습니다.")

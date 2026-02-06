from pydantic import BaseModel, Field
from typing import Optional


class SearchRequest(BaseModel):
    keyword: str = Field(..., min_length=1, description="검색할 키워드")
    blog_url: str = Field(..., min_length=1, description="확인할 블로그 URL (예: blog.naver.com/myblog)")


class BlogResult(BaseModel):
    rank: int = Field(..., description="검색 결과 순위")
    title: str = Field(..., description="블로그 글 제목")
    url: str = Field(..., description="블로그 글 URL")
    description: str = Field(default="", description="글 설명/미리보기")
    blog_name: str = Field(default="", description="블로그 이름")
    date: str = Field(default="", description="작성일")


class SearchResponse(BaseModel):
    success: bool = Field(..., description="검색 성공 여부")
    keyword: str = Field(..., description="검색한 키워드")
    is_exposed: bool = Field(default=False, description="블로그 노출 여부")
    exposed_rank: Optional[int] = Field(default=None, description="노출된 순위 (없으면 None)")
    exposed_result: Optional[BlogResult] = Field(default=None, description="노출된 결과 상세 정보")
    total_results: int = Field(default=0, description="전체 검색 결과 수")
    results: list[BlogResult] = Field(default=[], description="전체 검색 결과 목록")
    message: str = Field(default="", description="상태 메시지")

import requests
from bs4 import BeautifulSoup
import random
import time
import re
from urllib.parse import urlparse, unquote, parse_qs
from typing import Optional
from app.models.schemas import BlogResult, SearchResponse


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_headers() -> dict:
    """랜덤 User-Agent와 함께 요청 헤더 반환"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": "https://www.naver.com/",
        "Cache-Control": "max-age=0",
    }


def normalize_blog_url(url: str) -> str:
    """블로그 URL을 정규화하여 비교 가능한 형태로 변환"""
    url = unquote(url.lower().strip())

    # http/https 제거
    url = re.sub(r'^https?://', '', url)
    # www 제거
    url = re.sub(r'^www\.', '', url)
    # m. 제거 (모바일)
    url = re.sub(r'^m\.', '', url)
    # 끝의 슬래시 제거
    url = url.rstrip('/')

    # blog.me 형식을 blog.naver.com 형식으로 변환
    match = re.match(r'([a-zA-Z0-9_-]+)\.blog\.me/(\d+)', url)
    if match:
        return f"blog.naver.com/{match.group(1)}/{match.group(2)}"

    return url


def extract_post_id(url: str) -> Optional[str]:
    """블로그 URL에서 포스트 ID(숫자) 추출"""
    # blog.naver.com/blogid/12345 형식
    match = re.search(r'blog\.naver\.com/[^/]+/(\d+)', url)
    if match:
        return match.group(1)

    # blogid.blog.me/12345 형식
    match = re.search(r'\.blog\.me/(\d+)', url)
    if match:
        return match.group(1)

    return None


def search_naver_view(keyword: str, blog_url: str) -> SearchResponse:
    """네이버 통합 검색에서 특정 글 URL 노출 여부 확인"""

    # 입력된 글 URL 정규화
    target_url = normalize_blog_url(blog_url)
    target_post_id = extract_post_id(blog_url)

    # 네이버 통합 검색 URL
    search_url = f"https://search.naver.com/search.naver?query={keyword}"

    try:
        # 요청 전 랜덤 딜레이 (1~2초)
        time.sleep(random.uniform(1, 2))

        response = requests.get(search_url, headers=get_headers(), timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')

        results = []
        is_exposed = False
        exposed_rank = None
        exposed_result = None
        seen_urls = set()  # 중복 URL 제거용

        # 모든 블로그 링크 찾기 (포스트 ID가 있는 것만)
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href', '')

            # 블로그 포스트 링크인지 확인 (숫자 ID가 있는 것)
            if 'blog.naver.com' not in href:
                continue

            post_id = extract_post_id(href)
            if not post_id:
                continue

            # 중복 제거
            normalized_href = normalize_blog_url(href)
            if normalized_href in seen_urls:
                continue
            seen_urls.add(normalized_href)

            # 제목 추출 시도
            title = link.get_text(strip=True)

            # 부모 요소에서 더 많은 정보 추출 시도
            parent = link.find_parent(['div', 'li', 'article'])
            description = ""
            blog_name = ""
            date = ""

            if parent:
                # 설명 추출
                desc_elem = parent.select_one('[class*="dsc"]') or parent.select_one('[class*="desc"]')
                if desc_elem:
                    description = desc_elem.get_text(strip=True)

                # 날짜 추출
                date_elem = parent.select_one('[class*="date"]') or parent.select_one('[class*="time"]')
                if date_elem:
                    date = date_elem.get_text(strip=True)

            rank = len(results) + 1
            result = BlogResult(
                rank=rank,
                title=title if title else f"블로그 글 #{rank}",
                url=href,
                description=description,
                blog_name=blog_name,
                date=date
            )
            results.append(result)

            # URL 매칭 확인
            if target_post_id and post_id == target_post_id:
                is_exposed = True
                exposed_rank = rank
                exposed_result = result
            elif target_url in normalized_href or normalized_href in target_url:
                is_exposed = True
                exposed_rank = rank
                exposed_result = result

        if not results:
            return SearchResponse(
                success=True,
                keyword=keyword,
                is_exposed=False,
                total_results=0,
                results=[],
                message="검색 결과에서 블로그 글을 찾을 수 없습니다."
            )

        message = f"입력한 글이 {exposed_rank}위에 노출됩니다!" if is_exposed else f"입력한 글이 상위 {len(results)}개 결과에 노출되지 않습니다."

        return SearchResponse(
            success=True,
            keyword=keyword,
            is_exposed=is_exposed,
            exposed_rank=exposed_rank,
            exposed_result=exposed_result,
            total_results=len(results),
            results=results,
            message=message
        )

    except requests.exceptions.Timeout:
        return SearchResponse(
            success=False,
            keyword=keyword,
            message="요청 시간이 초과되었습니다. 잠시 후 다시 시도해주세요."
        )
    except requests.exceptions.RequestException as e:
        return SearchResponse(
            success=False,
            keyword=keyword,
            message=f"네트워크 오류가 발생했습니다: {str(e)}"
        )
    except Exception as e:
        return SearchResponse(
            success=False,
            keyword=keyword,
            message=f"오류가 발생했습니다: {str(e)}"
        )

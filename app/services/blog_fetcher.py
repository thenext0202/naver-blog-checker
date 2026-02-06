"""
블로그에서 제목으로 글 링크 찾기
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import Optional

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def get_blog_posts(blog_id: str) -> list:
    """블로그의 최근 글 목록 가져오기"""

    # 블로그 글 목록 페이지
    url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}&categoryNo=0&from=postList"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Referer": f"https://blog.naver.com/{blog_id}",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'lxml')
        posts = []

        # 글 목록에서 제목과 링크 추출
        # 방법 1: PostList에서 추출
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            title = link.get_text(strip=True)

            # 포스트 링크인지 확인
            match = re.search(r'/(\d+)(?:\?|$)', href)
            if match and title:
                post_id = match.group(1)
                posts.append({
                    'title': title,
                    'post_id': post_id,
                    'url': f"https://blog.naver.com/{blog_id}/{post_id}"
                })

        return posts

    except Exception as e:
        print(f"블로그 목록 가져오기 실패: {e}")
        return []


def get_blog_posts_rss(blog_id: str) -> list:
    """RSS 피드로 블로그 글 목록 가져오기"""

    url = f"https://rss.blog.naver.com/{blog_id}.xml"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "ko-KR,ko;q=0.9",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # lxml-xml 파서 사용
        soup = BeautifulSoup(response.text, 'lxml-xml')
        posts = []

        for item in soup.find_all('item'):
            title_elem = item.find('title')
            link_elem = item.find('link')
            guid_elem = item.find('guid')

            title = ""
            link = ""

            if title_elem:
                title = title_elem.get_text(strip=True)

            # link가 비어있으면 guid 사용
            if link_elem and link_elem.get_text(strip=True):
                link = link_elem.get_text(strip=True)
            elif guid_elem:
                link = guid_elem.get_text(strip=True)

            # ?fromRss 등 파라미터 제거
            link = re.sub(r'\?.*$', '', link)

            if title and link:
                # 포스트 ID 추출
                match = re.search(r'/(\d+)$', link)
                if match:
                    posts.append({
                        'title': title,
                        'post_id': match.group(1),
                        'url': link
                    })

        return posts

    except Exception as e:
        print(f"RSS 가져오기 실패: {e}")
        return []


def normalize_title(title: str) -> str:
    """제목 정규화 (비교용)"""
    # 공백, 특수문자 제거하고 소문자로
    title = re.sub(r'\s+', '', title)
    title = re.sub(r'[^\w가-힣]', '', title)
    return title.lower()


def find_post_by_title(blog_id: str, target_title: str) -> Optional[str]:
    """블로그에서 제목이 일치하는 글 찾기"""

    if not target_title.strip():
        return None

    target_normalized = normalize_title(target_title)

    # RSS 먼저 시도 (더 정확함)
    posts = get_blog_posts_rss(blog_id)

    if not posts:
        # RSS 실패하면 HTML 파싱
        posts = get_blog_posts(blog_id)

    for post in posts:
        post_normalized = normalize_title(post['title'])

        # 제목 일치 확인 (부분 일치도 허용)
        if target_normalized in post_normalized or post_normalized in target_normalized:
            return post['url']

        # 앞 20자 비교 (제목이 길 경우)
        if len(target_normalized) > 20 and len(post_normalized) > 20:
            if target_normalized[:20] == post_normalized[:20]:
                return post['url']

    return None


def extract_blog_id(url: str) -> Optional[str]:
    """블로그 URL에서 블로그 ID 추출"""

    # blog.naver.com/blogid 형식
    match = re.search(r'blog\.naver\.com/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)

    return None

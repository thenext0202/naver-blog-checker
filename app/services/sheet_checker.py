"""
구글 시트 노출 체크 서비스
"""
import gspread
from google.oauth2.service_account import Credentials
import os
import re
import time
import json
import threading
from app.services.naver_search import search_naver_view
from app.services.blog_fetcher import find_post_by_title, extract_blog_id

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# 전역 작업 상태
task_state = {
    "status": "idle",      # idle / running / paused / completed / stopped
    "current": 0,
    "total": 0,
    "message": "",
    "result": None,
}

SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '1me29DkuUo52Lf4MV2i38ZEpWKuOwEEhjtm8gt7jYRgU')
CREDS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'credentials.json')


def get_credentials():
    """환경변수 또는 파일에서 인증 정보 가져오기"""
    # 환경변수에서 JSON 문자열로 가져오기 (클라우드 배포용)
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if creds_json:
        creds_dict = json.loads(creds_json)
        return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)

    # 파일에서 가져오기 (로컬 개발용)
    if os.path.exists(CREDS_PATH):
        return Credentials.from_service_account_file(CREDS_PATH, scopes=SCOPES)

    return None


def parse_date(date_str: str) -> tuple:
    """월/일 형식 파싱 -> (월, 일) 튜플 반환"""
    try:
        parts = date_str.strip().split('/')
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))
    except:
        pass
    return None


def is_date_in_range(date_str: str, start_date: str, end_date: str) -> bool:
    """날짜가 범위 내에 있는지 확인"""
    date = parse_date(date_str)
    start = parse_date(start_date)
    end = parse_date(end_date)

    if not date or not start or not end:
        return False

    date_num = date[0] * 100 + date[1]
    start_num = start[0] * 100 + start[1]
    end_num = end[0] * 100 + end[1]

    return start_num <= date_num <= end_num


def has_post_id(url: str) -> bool:
    """URL에 포스트 ID가 있는지 확인"""
    return bool(re.search(r'/\d+(?:\?.*)?$', url.rstrip("'")))


def _wait_if_paused():
    """일시정지 상태이면 재개될 때까지 대기. stopped이면 True 반환."""
    while task_state["status"] == "paused":
        time.sleep(0.5)
    return task_state["status"] == "stopped"


def check_sheet_exposure(start_date: str, end_date: str) -> dict:
    """
    구글 시트에서 기간 내 데이터 처리

    1단계: 링크 업데이트 (블로그 홈 → 실제 글 링크)
    2단계: 노출 체크

    조건:
    - A열 날짜가 start_date ~ end_date 범위 내
    - T열 = TRUE
    - W열 = 비어있음
    """

    task_state["status"] = "running"
    task_state["current"] = 0
    task_state["total"] = 0
    task_state["message"] = "시트 데이터 로딩 중..."
    task_state["result"] = None

    creds = get_credentials()
    if not creds:
        result = {"success": False, "message": "인증 정보가 없습니다. (credentials.json 또는 GOOGLE_CREDENTIALS 환경변수)"}
        task_state["status"] = "completed"
        task_state["result"] = result
        return result

    try:
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_ID).worksheet("발행")

        all_values = sheet.get_all_values()

        # 1단계: 링크 업데이트 (Q열에 포스트ID 없고 T열=TRUE인 행)
        links_updated = 0
        task_state["message"] = "링크 업데이트 중..."

        for row_idx in range(2, len(all_values)):
            if _wait_if_paused():
                result = {"success": True, "message": f"중단됨. 링크 {links_updated}개 업데이트", "processed": 0, "exposed": 0, "links_updated": links_updated}
                task_state["status"] = "stopped"
                task_state["result"] = result
                return result

            row = all_values[row_idx]

            a_val = row[0].strip() if len(row) > 0 else ""  # A열 (날짜)
            t_val = row[19].strip().upper() if len(row) > 19 else ""  # T열
            link = row[16].strip() if len(row) > 16 else ""  # Q열
            title = row[14].strip() if len(row) > 14 else ""  # O열

            # 조건: 기간 내 & T열=TRUE & Q열에 포스트ID 없음 & 제목 있음
            if (is_date_in_range(a_val, start_date, end_date) and
                t_val == "TRUE" and
                link and not has_post_id(link) and title):

                blog_id = extract_blog_id(link)
                if blog_id:
                    new_url = find_post_by_title(blog_id, title)
                    if new_url:
                        sheet.update_cell(row_idx + 1, 17, new_url)  # Q열 업데이트
                        links_updated += 1
                        time.sleep(0.5)

        # 시트 데이터 다시 읽기 (링크 업데이트 반영)
        if links_updated > 0:
            all_values = sheet.get_all_values()

        # 2단계: 노출 체크할 행 필터링
        rows_to_process = []
        for row_idx in range(2, len(all_values)):
            row = all_values[row_idx]

            a_val = row[0].strip() if len(row) > 0 else ""  # A열 (날짜)
            t_val = row[19].strip().upper() if len(row) > 19 else ""  # T열
            w_val = row[22].strip() if len(row) > 22 else ""  # W열
            keyword = row[4].strip() if len(row) > 4 else ""  # E열
            link = row[16].strip() if len(row) > 16 else ""  # Q열

            # 조건: 기간 내 & T열=TRUE & W열=비어있음 & 키워드/링크 있음 & 포스트ID 있음
            if (is_date_in_range(a_val, start_date, end_date) and
                t_val == "TRUE" and
                w_val == "" and
                keyword and link and has_post_id(link)):
                rows_to_process.append({
                    'row_num': row_idx + 1,
                    'keyword': keyword,
                    'link': link
                })

        if not rows_to_process and links_updated == 0:
            result = {
                "success": True,
                "message": f"처리할 데이터가 없습니다. (기간: {start_date} ~ {end_date})",
                "processed": 0,
                "exposed": 0,
                "links_updated": 0
            }
            task_state["status"] = "completed"
            task_state["result"] = result
            return result

        # 노출 체크
        processed = 0
        exposed = 0
        task_state["total"] = len(rows_to_process)
        task_state["message"] = f"노출 체크 중... (0/{len(rows_to_process)})"

        for row_data in rows_to_process:
            if _wait_if_paused():
                result = {"success": True, "message": f"중단됨. 링크 {links_updated}개 업데이트, {processed}개 노출체크, {exposed}개 노출됨", "processed": processed, "exposed": exposed, "links_updated": links_updated}
                task_state["status"] = "stopped"
                task_state["result"] = result
                return result

            link = row_data['link']
            keyword = row_data['keyword']
            row_num = row_data['row_num']

            result = search_naver_view(keyword, link)

            if result.is_exposed:
                rank_value = str(result.exposed_rank)
                exposed += 1
            else:
                rank_value = "-"

            sheet.update_cell(row_num, 23, rank_value)  # W열
            processed += 1
            task_state["current"] = processed
            task_state["message"] = f"노출 체크 중... ({processed}/{len(rows_to_process)})"
            time.sleep(0.5)

        result = {
            "success": True,
            "message": f"완료! 링크 {links_updated}개 업데이트, {processed}개 노출체크, {exposed}개 노출됨",
            "processed": processed,
            "exposed": exposed,
            "links_updated": links_updated
        }
        task_state["status"] = "completed"
        task_state["message"] = result["message"]
        task_state["result"] = result
        return result

    except Exception as e:
        result = {"success": False, "message": f"오류: {str(e)}"}
        task_state["status"] = "completed"
        task_state["result"] = result
        return result


def start_check_in_background(start_date: str, end_date: str):
    """백그라운드 스레드에서 노출 체크 실행"""
    thread = threading.Thread(
        target=check_sheet_exposure,
        args=(start_date, end_date),
        daemon=True
    )
    thread.start()

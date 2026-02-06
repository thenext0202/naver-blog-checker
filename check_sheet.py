#!/usr/bin/env python3 -u
"""
구글 시트 연동 노출 체크 스크립트
- 탭: 발행
- 조건: T열이 TRUE이고 V열이 비어있는 행만
- E열: 키워드
- Q열: 블로그 링크
- W열: 순위 결과 (순위 또는 "-")
"""
import gspread
from google.oauth2.service_account import Credentials
import time
import sys
import os
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.services.naver_search import search_naver_view

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SPREADSHEET_ID = '1me29DkuUo52Lf4MV2i38ZEpWKuOwEEhjtm8gt7jYRgU'

# 열 인덱스 (0부터 시작)
KEYWORD_COL = 4   # E열
LINK_COL = 16     # Q열
CHECK_COL = 19    # T열 (체크박스)
EMPTY_COL = 21    # V열 (비어있어야 함)
RESULT_COL = 23   # W열 (결과 기입, 1부터 시작하는 인덱스)


def main():
    creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')

    if not os.path.exists(creds_path):
        print(f"오류: {creds_path} 파일이 없습니다.")
        return

    print("구글 시트 연결 중...")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheet = spreadsheet.worksheet("발행")
    print(f"시트 '발행' 연결 완료")

    all_values = sheet.get_all_values()
    total_rows = len(all_values)
    print(f"총 {total_rows}행")

    # 처리할 행 필터링 (3행부터, T열=TRUE, V열=비어있음)
    rows_to_process = []
    for row_idx in range(2, total_rows):  # 3행부터 (0-indexed: 2)
        row = all_values[row_idx]

        # T열 체크 (TRUE인지)
        t_val = row[CHECK_COL].strip().upper() if len(row) > CHECK_COL else ""
        # V열 체크 (비어있는지)
        v_val = row[EMPTY_COL].strip() if len(row) > EMPTY_COL else ""
        # 키워드와 링크 존재 여부
        keyword = row[KEYWORD_COL].strip() if len(row) > KEYWORD_COL else ""
        link = row[LINK_COL].strip() if len(row) > LINK_COL else ""

        if t_val == "TRUE" and v_val == "" and keyword and link:
            rows_to_process.append((row_idx + 1, keyword, link))  # row_idx+1 = 실제 행번호

    print(f"처리할 행: {len(rows_to_process)}개")

    if not rows_to_process:
        print("처리할 행이 없습니다.")
        return

    updated_count = 0
    for i, (row_num, keyword, link) in enumerate(rows_to_process):
        print(f"\n[{i+1}/{len(rows_to_process)}] {row_num}행: {keyword[:20]}...")

        try:
            result = search_naver_view(keyword, link)

            if result.is_exposed:
                rank_value = str(result.exposed_rank)
                print(f"  → {rank_value}위 노출!")
            else:
                rank_value = "-"
                print(f"  → 노출 안됨")

            sheet.update_cell(row_num, RESULT_COL, rank_value)
            updated_count += 1

            # API 제한 방지
            time.sleep(1)

        except Exception as e:
            print(f"  → 오류: {e}")
            sheet.update_cell(row_num, RESULT_COL, "오류")
            time.sleep(1)

    print(f"\n완료! {updated_count}개 행 업데이트됨")


if __name__ == "__main__":
    main()

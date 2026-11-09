from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
from bs4 import BeautifulSoup

app = FastAPI()

# 깃허브 페이지에서 API를 자유롭게 호출할 수 있도록 CORS 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ENCOM_LOGIN_URL = "https://selfdesk.e-ncom.co.kr/main/loginOk.do"
ENCOM_LIST_URL = "https://selfdesk.e-ncom.co.kr/selfUse/reserveList.do"

USER_ID = "이천시노인종합복지관"
USER_PW = "*old0190"
ORG_ID = "9437"

@app.get("/api/reservations")
def get_reservations(date: str = None):
    # 테스트 기간 동안은 2026-11-09 로 날짜 고정 (최종 배포 시 아래 주석 해제)
    if not date:
        date = "2026-11-09"
        # date = datetime.now().strftime("%Y-%m-%d") # 실제 오늘 날짜 자동 사용 시 적용
        
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://selfdesk.e-ncom.co.kr/selfUse/reserveList.do",
        "Origin": "https://selfdesk.e-ncom.co.kr"
    }

    # 1. 초기 쿠키 생성
    session.get("https://selfdesk.e-ncom.co.kr/login/login.do", headers=headers)

    # 2. AJAX 로그인
    ajax_headers = headers.copy()
    ajax_headers["X-Requested-With"] = "XMLHttpRequest"

    login_payload = {
        "orgId": ORG_ID,
        "userId": USER_ID,
        "userPw": USER_PW
    }

    login_res = session.post(ENCOM_LOGIN_URL, data=login_payload, headers=ajax_headers)
    
    try:
        if login_res.json().get("result") != "Y":
            raise HTTPException(status_code=401, detail="엔컴 로그인 실패")
    except Exception:
        raise HTTPException(status_code=500, detail="엔컴 로그인 응답 에러")

    # 3. 스크린파크골프(programId=34) 예약 목록 POST 요청
    search_payload = {
        "resveDate": date,
        "programId": "34"
    }

    list_res = session.post(ENCOM_LIST_URL, data=search_payload, headers=ajax_headers)
    soup = BeautifulSoup(list_res.text, "html.parser")
    rows = soup.select("table tr")

    reservations = []
    
    for row in rows[1:]:
        cols = row.find_all(["td", "th"])
        if len(cols) >= 3:
            time_slot = cols[0].get_text(strip=True)
            court1_members = [s for s in cols[1].stripped_strings]
            court2_members = [s for s in cols[2].stripped_strings]
            
            reservations.append({
                "time": time_slot,
                "court1": court1_members if court1_members else ["예약 없음"],
                "court2": court2_members if court2_members else ["예약 없음"]
            })

    return {
        "date": date,
        "program": "스크린파크골프",
        "data": reservations
    }
import streamlit as st
import json
import os
from datetime import datetime, date
from typing import List, Dict, Optional
import os.path
import hashlib

# 페이지 설정
st.set_page_config(
    page_title="농구장/운동장 예약 시스템",
    page_icon="🏀",
    layout="wide"
)

# 데이터 파일 경로
DATA_DIR = "data"
BASKETBALL_FILE = os.path.join(DATA_DIR, "basketball_reservations.json")
PLAYGROUND_FILE = os.path.join(DATA_DIR, "playground_reservations.json")

# 데이터 디렉토리 생성
os.makedirs(DATA_DIR, exist_ok=True)

def load_reservations(file_path: str) -> List[Dict]:
    """예약 데이터 로드"""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_reservations(file_path: str, reservations: List[Dict]):
    """예약 데이터 저장"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(reservations, f, ensure_ascii=False, indent=2)

def hash_password(password: str) -> str:
    """비밀번호 해시"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def remove_reservation_by_timestamp(reservations: List[Dict], reserved_at: str):
    """reserved_at 값으로 예약 삭제"""
    remaining: List[Dict] = []
    removed: Optional[Dict] = None
    for reservation in reservations:
        if reservation.get('reserved_at') == reserved_at:
            removed = reservation
        else:
            remaining.append(reservation)
    return remaining, removed

def cancel_basketball_reservation(reservations: List[Dict], reserved_at: str):
    """농구장 예약 취소 및 대결 상대 정보 업데이트"""
    updated_reservations, removed = remove_reservation_by_timestamp(reservations, reserved_at)
    if not removed:
        return reservations, False

    if removed.get('mode') == '대결하기':
        for reservation in updated_reservations:
            if (
                reservation.get('mode') == '대결하기' and
                reservation['date'] == removed['date'] and
                reservation['time_slot'] == removed['time_slot']
            ):
                if reservation.get('opponent_team') == removed.get('team'):
                    reservation['opponent_team'] = None
                if (
                    removed.get('opponent_team') and
                    reservation.get('team') == removed['opponent_team']
                ):
                    reservation['opponent_team'] = None

    return updated_reservations, True

def cancel_generic_reservation(reservations: List[Dict], reserved_at: str):
    """운동장 등 일반 예약 취소"""
    updated_reservations, removed = remove_reservation_by_timestamp(reservations, reserved_at)
    return updated_reservations, removed is not None

def check_duplicate_reservation(reservations: List[Dict], date_str: str, time_slot: str) -> bool:
    """중복 예약 체크"""
    for reservation in reservations:
        if reservation['date'] == date_str and reservation['time_slot'] == time_slot:
            return True
    return False

def format_date(date_obj: date) -> str:
    """날짜를 문자열로 변환"""
    return date_obj.strftime("%Y-%m-%d")

def basketball_reservation_page():
    """농구장 예약 페이지"""
    st.header("🏀 농구장 예약")
    
    # 예약 모드 선택
    reservation_mode = st.radio(
        "예약 모드를 선택하세요:",
        ["일반 예약", "대결하기"],
        horizontal=True
    )
    
    # 날짜 선택
    selected_date = st.date_input(
        "예약할 날짜를 선택하세요:",
        min_value=date.today(),
        value=date.today()
    )
    date_str = format_date(selected_date)
    
    # 시간 선택
    time_slot = st.selectbox(
        "시간대를 선택하세요:",
        ["점심시간", "방과후"]
    )
    
    # 예약자 정보
    st.subheader("예약자 정보")
    student_id = st.text_input("학번을 입력하세요:")
    student_name = st.text_input("이름을 입력하세요:")
    password = st.text_input("예약 비밀번호를 입력하세요:", type="password", key="basketball_password")
    
    # 대결하기 모드
    if reservation_mode == "대결하기":
        st.subheader("팀 구성")
        st.info("각 팀은 5명으로 구성됩니다.")
        
        # 내 팀 구성
        st.markdown("### 내 팀 구성")
        my_team = []
        for i in range(5):
            player = st.text_input(f"팀원 {i+1} 이름:", key=f"my_team_{i}")
            if player:
                my_team.append(player)
        
        # 기존 예약 확인 (대결 상대 찾기)
        reservations = load_reservations(BASKETBALL_FILE)
        existing_match = None
        for reservation in reservations:
            if (reservation['date'] == date_str and 
                reservation['time_slot'] == time_slot and 
                reservation.get('mode') == '대결하기' and
                reservation.get('opponent_team') is None):
                existing_match = reservation
                break
        
        if existing_match:
            st.success(f"대결 상대를 찾았습니다! 상대 팀: {', '.join(existing_match['team'])}")
            st.markdown("### 상대 팀")
            for i, player in enumerate(existing_match['team'], 1):
                st.text(f"팀원 {i}: {player}")
        
        # 예약 버튼
        if st.button("예약하기", type="primary"):
            if not student_id or not student_name:
                st.error("학번과 이름을 모두 입력해주세요.")
            elif len(my_team) < 5:
                st.error("팀원 5명을 모두 입력해주세요.")
            elif not password:
                st.error("예약 비밀번호를 입력해주세요.")
            else:
                reservations = load_reservations(BASKETBALL_FILE)
                is_joining_match = (
                    existing_match is not None and
                    existing_match.get('opponent_team') is None
                )

                # 중복 예약 체크 (새로운 대결 예약일 때만)
                if not is_joining_match and check_duplicate_reservation(reservations, date_str, time_slot):
                    st.error("❌ 이미 예약이 되어있습니다. 다른 날짜나 시간을 선택해주세요.")
                else:
                    reservation_data = {
                        'date': date_str,
                        'time_slot': time_slot,
                        'student_id': student_id,
                        'student_name': student_name,
                        'mode': '대결하기',
                        'team': my_team,
                        'opponent_team': existing_match['team'] if existing_match else None,
                        'reserved_at': datetime.now().isoformat(),
                        'password_hash': hash_password(password)
                    }
                    
                    # 기존 대결 예약이 있으면 상대팀 정보 업데이트
                    if existing_match:
                        for i, res in enumerate(reservations):
                            if (res['date'] == date_str and 
                                res['time_slot'] == time_slot and 
                                res.get('mode') == '대결하기' and
                                res.get('opponent_team') is None):
                                reservations[i]['opponent_team'] = my_team
                                break
                    
                    reservations.append(reservation_data)
                    save_reservations(BASKETBALL_FILE, reservations)
                    st.success("✅ 예약되었습니다!")
                    st.balloons()
    
    else:  # 일반 예약
        if st.button("예약하기", type="primary"):
            if not student_id or not student_name:
                st.error("학번과 이름을 모두 입력해주세요.")
            elif not password:
                st.error("예약 비밀번호를 입력해주세요.")
            else:
                reservations = load_reservations(BASKETBALL_FILE)
                
                # 중복 예약 체크
                if check_duplicate_reservation(reservations, date_str, time_slot):
                    st.error("❌ 이미 예약이 되어있습니다. 다른 날짜나 시간을 선택해주세요.")
                else:
                    reservation_data = {
                        'date': date_str,
                        'time_slot': time_slot,
                        'student_id': student_id,
                        'student_name': student_name,
                        'mode': '일반',
                        'reserved_at': datetime.now().isoformat(),
                        'password_hash': hash_password(password)
                    }
                    reservations.append(reservation_data)
                    save_reservations(BASKETBALL_FILE, reservations)
                    st.success("✅ 예약되었습니다!")
                    st.balloons()

    st.divider()
    st.subheader("❌ 예약 취소")

    if not student_id or not student_name:
        st.info("예약을 취소하려면 학번과 이름을 먼저 입력해주세요.")
    else:
        all_reservations = load_reservations(BASKETBALL_FILE)
        my_reservations = [
            reservation for reservation in all_reservations
            if reservation['student_id'] == student_id and reservation['student_name'] == student_name
        ]

        if not my_reservations:
            st.info("해당 정보로 등록된 예약이 없습니다.")
        else:
            selected_reservation = st.selectbox(
                "취소할 예약을 선택하세요:",
                options=my_reservations,
                format_func=lambda r: f"📅 {r['date']} - {r['time_slot']} ({r.get('mode', '일반')})",
                key="basketball_cancel_select"
            )

            cancel_password = st.text_input(
                "예약 비밀번호를 입력하세요:",
                type="password",
                key="basketball_cancel_password"
            )

            if st.button("선택한 예약 취소", type="secondary", key="basketball_cancel_button"):
                password_hash = selected_reservation.get('password_hash')
                if password_hash:
                    if not cancel_password:
                        st.error("비밀번호를 입력해주세요.")
                        return
                    if hash_password(cancel_password) != password_hash:
                        st.error("비밀번호가 일치하지 않습니다.")
                        return

                updated_reservations, cancelled = cancel_basketball_reservation(
                    all_reservations,
                    selected_reservation['reserved_at']
                )
                if cancelled:
                    save_reservations(BASKETBALL_FILE, updated_reservations)
                    st.success("✅ 예약이 취소되었습니다.")
                    try:
                        st.rerun()
                    except AttributeError:
                        st.experimental_rerun()
                else:
                    st.error("❌ 예약 취소에 실패했습니다. 다시 시도해주세요.")

def playground_reservation_page():
    """운동장 예약 페이지"""
    st.header("⚽ 운동장 예약")
    
    # 날짜 선택
    selected_date = st.date_input(
        "예약할 날짜를 선택하세요:",
        min_value=date.today(),
        value=date.today()
    )
    date_str = format_date(selected_date)
    
    # 시간 선택
    time_slot = st.selectbox(
        "시간대를 선택하세요:",
        ["점심시간", "방과후"]
    )
    
    # 예약자 정보
    st.subheader("예약자 정보")
    student_id = st.text_input("학번을 입력하세요:")
    student_name = st.text_input("이름을 입력하세요:")
    password = st.text_input("예약 비밀번호를 입력하세요:", type="password", key="playground_password")
    
    if st.button("예약하기", type="primary"):
        if not student_id or not student_name:
            st.error("학번과 이름을 모두 입력해주세요.")
        elif not password:
            st.error("예약 비밀번호를 입력해주세요.")
        else:
            reservations = load_reservations(PLAYGROUND_FILE)
            
            # 중복 예약 체크
            if check_duplicate_reservation(reservations, date_str, time_slot):
                st.error("❌ 이미 예약이 되어있습니다. 다른 날짜나 시간을 선택해주세요.")
            else:
                reservation_data = {
                    'date': date_str,
                    'time_slot': time_slot,
                    'student_id': student_id,
                    'student_name': student_name,
                    'reserved_at': datetime.now().isoformat(),
                    'password_hash': hash_password(password)
                }
                reservations.append(reservation_data)
                save_reservations(PLAYGROUND_FILE, reservations)
                st.success("✅ 예약되었습니다!")
                st.balloons()

    st.divider()
    st.subheader("❌ 예약 취소")

    if not student_id or not student_name:
        st.info("예약을 취소하려면 학번과 이름을 먼저 입력해주세요.")
    else:
        all_reservations = load_reservations(PLAYGROUND_FILE)
        my_reservations = [
            reservation for reservation in all_reservations
            if reservation['student_id'] == student_id and reservation['student_name'] == student_name
        ]

        if not my_reservations:
            st.info("해당 정보로 등록된 예약이 없습니다.")
        else:
            selected_reservation = st.selectbox(
                "취소할 예약을 선택하세요:",
                options=my_reservations,
                format_func=lambda r: f"📅 {r['date']} - {r['time_slot']}",
                key="playground_cancel_select"
            )

            cancel_password = st.text_input(
                "예약 비밀번호를 입력하세요:",
                type="password",
                key="playground_cancel_password"
            )

            if st.button("선택한 예약 취소", type="secondary", key="playground_cancel_button"):
                password_hash = selected_reservation.get('password_hash')
                if password_hash:
                    if not cancel_password:
                        st.error("비밀번호를 입력해주세요.")
                        return
                    if hash_password(cancel_password) != password_hash:
                        st.error("비밀번호가 일치하지 않습니다.")
                        return

                updated_reservations, cancelled = cancel_generic_reservation(
                    all_reservations,
                    selected_reservation['reserved_at']
                )
                if cancelled:
                    save_reservations(PLAYGROUND_FILE, updated_reservations)
                    st.success("✅ 예약이 취소되었습니다.")
                    try:
                        st.rerun()
                    except AttributeError:
                        st.experimental_rerun()
                else:
                    st.error("❌ 예약 취소에 실패했습니다. 다시 시도해주세요.")

def view_reservations_page():
    """예약 조회 페이지"""
    st.header("📋 예약 조회")
    
    # 탭으로 농구장/운동장 구분
    tab1, tab2 = st.tabs(["농구장 예약", "운동장 예약"])
    
    with tab1:
        st.subheader("농구장 예약 목록")
        reservations = load_reservations(BASKETBALL_FILE)
        
        if not reservations:
            st.info("예약된 내역이 없습니다.")
        else:
            # 날짜별로 정렬
            reservations.sort(key=lambda x: x['date'])
            
            for reservation in reservations:
                with st.expander(f"📅 {reservation['date']} - {reservation['time_slot']} ({reservation['mode']})"):
                    st.write(f"**예약자:** {reservation['student_name']} ({reservation['student_id']})")
                    if reservation.get('mode') == '대결하기':
                        st.write(f"**내 팀:** {', '.join(reservation['team'])}")
                        if reservation.get('opponent_team'):
                            st.write(f"**상대 팀:** {', '.join(reservation['opponent_team'])}")
                        else:
                            st.info("아직 상대팀이 없습니다.")
                    st.write(f"**예약 시간:** {reservation['reserved_at']}")
    
    with tab2:
        st.subheader("운동장 예약 목록")
        reservations = load_reservations(PLAYGROUND_FILE)
        
        if not reservations:
            st.info("예약된 내역이 없습니다.")
        else:
            # 날짜별로 정렬
            reservations.sort(key=lambda x: x['date'])
            
            for reservation in reservations:
                with st.expander(f"📅 {reservation['date']} - {reservation['time_slot']}"):
                    st.write(f"**예약자:** {reservation['student_name']} ({reservation['student_id']})")
                    st.write(f"**예약 시간:** {reservation['reserved_at']}")

def main():
    """메인 함수"""
    st.title("🏀 농구장/운동장 예약 시스템")
    st.markdown("---")
    
    # 사이드바 메뉴
    st.sidebar.title("메뉴")
    page = st.sidebar.radio(
        "페이지를 선택하세요:",
        ["농구장 예약", "운동장 예약", "예약 조회"]
    )
    
    # 페이지 라우팅
    if page == "농구장 예약":
        basketball_reservation_page()
    elif page == "운동장 예약":
        playground_reservation_page()
    elif page == "예약 조회":
        view_reservations_page()
    
    # 사이드바에 정보 표시
    st.sidebar.markdown("---")
    st.sidebar.info("""
    **사용 방법:**
    1. 원하는 시설을 선택하세요
    2. 날짜와 시간을 선택하세요
    3. 예약자 정보를 입력하세요
    4. 대결하기는 팀원 5명을 입력하세요
    """)

if __name__ == "__main__":
    main()


import streamlit as st
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    st.set_page_config(
        page_title="Autonomous Database Connection",
        page_icon="🔌",
        layout="wide"
    )

    # 사이드바 메뉴
    with st.sidebar:
        st.title("📱 앱 메뉴")
        selected_menu = st.radio(
            "메뉴를 선택하세요",
            options=["Autonomous DB 연결"],
            index=0,
            key="menu"
        )
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ℹ️ 정보")
        st.sidebar.markdown("현재 버전: v1.0.0")

    # 메인 컨텐츠
    if selected_menu == "Autonomous DB 연결":
        st.title("🔌 Autonomous DB 연결")

    # Connection settings section
    st.header("연결 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("사용자명", key="username", placeholder="사용자명을 입력하세요")
        st.text_input("비밀번호", type="password", key="password", placeholder="비밀번호를 입력하세요")
        
    with col2:
        st.text_input("호스트", key="host", placeholder="호스트 주소를 입력하세요")
        st.text_input("포트", key="port", placeholder="포트 번호를 입력하세요", value="1521")
        
    # Service name and wallet file upload
    st.text_input("서비스명", key="service_name", placeholder="서비스명을 입력하세요")
    
    wallet_file = st.file_uploader("Wallet 파일 업로드 (ZIP)", type=['zip'])
    
    # Connection test button
    if st.button("연결 테스트", type="primary"):
        with st.spinner("연결 테스트 중..."):
            # Connection test logic will be implemented later
            st.info("연결 테스트 기능은 다음 업데이트에서 구현될 예정입니다")
    
    # Additional features section
    st.header("데이터베이스 작업")
    
    # Query section
    st.subheader("SQL 쿼리")
    query = st.text_area("SQL 쿼리를 입력하세요", height=150)
    
    col3, col4 = st.columns([1, 4])
    with col3:
        if st.button("쿼리 실행"):
            st.info("쿼리 실행 기능은 다음 업데이트에서 구현될 예정입니다")
    
    with col4:
        st.empty()  # Placeholder for query results

    # Footer
    st.markdown("---")
    st.markdown("Streamlit으로 만들어진 애플리케이션 ❤️")

if __name__ == "__main__":
    main()

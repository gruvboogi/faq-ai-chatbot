import streamlit as st
import oracledb
import json
import os

# 페이지 설정
st.set_page_config(
    page_title="Oracle AI SELECT Demo",
    page_icon="🤖",
    layout="wide"
)

# 제목
st.title("Oracle AI SELECT Demo")
st.markdown("""
이 앱은 Oracle Autonomous Database의 AI SELECT 기능을 사용하여 자연어로 데이터베이스를 쿼리할 수 있습니다.
""")

# 데이터베이스 설정 파일 로드
try:
    with open("db_config.json", "r") as file:
        config = json.load(file)
        un = config["DB_USER"]
        pw = config["DB_PASSWORD"]
        dsn = config["DSN"]
        wallet_pw = config["WALLET_PASSWORD"]
        
    # 데이터베이스 연결
    connection = oracledb.connect(
        config_dir='./wallet',
        user=un,
        password=pw,
        dsn=dsn,
        wallet_location='./wallet',
        wallet_password=wallet_pw
    )
    
    # AI 프로필 설정
    with connection.cursor() as cursor:
        create_table_sql = """
        BEGIN
            DBMS_CLOUD_AI.set_profile(profile_name => 'OCI_GENERATIVE_AI_PROFILE');
        END;
        """
        cursor.execute(create_table_sql)
        connection.autocommit = True
    
    st.success("데이터베이스 연결 성공!")
    
    # 메인 컨텐츠
    st.header("AI 쿼리 입력")
    
    # Action 선택
    action = st.radio(
        "Select Action:",
        ["showsql", "runsql", "narrate", "explainsql"],
        index=0,  # showsql을 기본값으로 설정
        horizontal=True
    )
    
    user_input = st.text_input("자연어로 쿼리를 입력하세요:", 
                             placeholder="예: how many marketing reports do I have")
    
    if st.button("실행"):
        with connection.cursor() as cursor:
            query = f"SELECT AI {action} {user_input}"
            
            # 생성된 쿼리 표시
            st.subheader("생성된 쿼리:")
            st.code(query, language="sql")
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            if rows:
                st.subheader("쿼리 결과:")
                for i, row in enumerate(rows, 1):
                    st.markdown(f"**결과 {i}:**")
                    for j, value in enumerate(row, 1):
                        st.code(f"컬럼 {j}: {value}", language="sql")
                
                # 응답 객체 표시
                st.subheader("응답 객체:")
                st.json({
                    "query": query,
                    "response": rows
                })
            else:
                st.info("결과가 없습니다.")
    
except FileNotFoundError:
    st.error("db_config.json 파일을 찾을 수 없습니다. 파일이 현재 디렉토리에 있는지 확인해주세요.")
except json.JSONDecodeError:
    st.error("db_config.json 파일의 형식이 올바르지 않습니다.")
except Exception as e:
    st.error(f"오류 발생: {str(e)}") 
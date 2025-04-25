import streamlit as st

# 사이드바 메뉴 생성
menu = st.sidebar.radio("선택", ["Basic", "Season", "EmbV2", "Tagalog", "English", "Marketing", "Cohere", "Llama"])

# 메뉴에 따라 다른 파일 실행
if menu == "Basic":
    exec(open("./st_basic_faq_chatbot.py", encoding="utf-8").read())
elif menu == "Season":
    exec(open("./st_season_faq_chatbot.py", encoding="utf-8").read())
elif menu == "EmbV2":
    exec(open("./st_season_faq_chatbot-embv2.py", encoding="utf-8").read())
elif menu == "Tagalog":
    exec(open("./st_season_faq_chatbot_tl.py", encoding="utf-8").read())    
elif menu == "English":
    exec(open("./st_season_faq_chatbot_en.py", encoding="utf-8").read())  
elif menu == "Marketing":
    exec(open("./st_marketing_report.py", encoding="utf-8").read())    
elif menu == "Cohere":
    exec(open("./st_season_faq_chatbot-cohere-test.py", encoding="utf-8").read())    
elif menu == "Llama":
    exec(open("./st_season_faq_chatbot-llama-test.py", encoding="utf-8").read())    
    
st.sidebar.markdown("---")
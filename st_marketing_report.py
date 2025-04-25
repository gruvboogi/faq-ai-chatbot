from transformers import LlamaTokenizerFast
from sentence_transformers import SentenceTransformer
import sys
import streamlit as st
import oracledb
import oci
import array 
import json

#encoder
encoder = SentenceTransformer('jhgan/ko-sroberta-multitask')
table_name = 'marketing_report_narative'

# JSON 파일에서 사용자 이름과 비밀번호 읽기
with open("db_config.json", "r") as file:
    config = json.load(file)
    un = config["DB_USER"]
    pw = config["DB_PASSWORD"]
    dsn = config["DSN"]
    wallet_pw = config["WALLET_PASSWORD"]
    comp_id = config["COMPARTMENT_ID"]


connection = oracledb.connect(
   config_dir='./wallet',
   user=un,
   password=pw,
   dsn=dsn,
   wallet_location='./wallet',
   wallet_password=wallet_pw)

# OCI Config 설정
compartment_id = comp_id
CONFIG_PROFILE = "DEFAULT"
config = oci.config.from_file('config', CONFIG_PROFILE)

# Service endpoint(us-chicago-1, ap-osaka-1, sa-saopaulo-1, uk-london-1, eu-frankfurt-1)
# pretrained model : https://docs.oracle.com/en-us/iaas/Content/generative-ai/pretrained-models.htm
#endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
endpoint = "https://inference.generativeai.ap-osaka-1.oci.oraclecloud.com"

# GenAI client
generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config=config, service_endpoint=endpoint, 
    retry_strategy=oci.retry.NoneRetryStrategy(), timeout=(10, 240)
)

#topK 3 fetch
topK = 2

sql = f"""select payload, vector_distance(vector, :vector, COSINE) as score
from {table_name}
order by score
fetch approx first {topK} rows only"""

# OCI Generative AI API 호출 함수
def get_cohere_response(prompt):
    chat_detail = oci.generative_ai_inference.models.ChatDetails()

    chat_request = oci.generative_ai_inference.models.CohereChatRequest()
    chat_request.message = prompt
    chat_request.max_tokens = 500
    chat_request.temperature = 0.0
    chat_request.frequency_penalty = 0
    chat_request.top_p = 1
    chat_request.top_k = 0

    chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id="cohere.command-r-plus-08-2024")
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = compartment_id
    chat_response = generative_ai_inference_client.chat(chat_detail)
    message = chat_response.data.chat_response.chat_history[1].message
    return message

def truncate_string(string, max_tokens):
    # Tokenize the text and count the tokens
    tokens = tokenizer.encode(string, add_special_tokens=False) 
    # Truncate the tokens to a maximum length
    truncated_tokens = tokens[:max_tokens]
    # transform the tokens back to text
    truncated_text = tokenizer.decode(truncated_tokens)
    return truncated_text

# ADB Query 함수
def vector_search(connection, encoder, user_input, sql):
    with connection.cursor() as cursor:
        embedding = list(encoder.encode(user_input))
        vector = array.array("f", embedding)
        
        results = []
        for (info, score,) in cursor.execute(sql, vector=vector):
            text_content = info.read()
            results.append((score, json.loads(text_content)))
        
        return results

def select_ai(connection, select_ai_sql):
    with connection.cursor() as cursor:
        # Define the query to select all rows from a table
        query = f"SELECT AI {select_ai_sql}"
    
        # Execute the query
        cursor.execute(query)
    
        # Fetch all rows
        rows = cursor.fetchall()
    
        # Print the rows
        for row in rows[:1]:
            return row[0]

        
debug = "1"

def log_text_area(string, target, height):
    if debug == "1":
        try:
            st.text_area(string, target, height)
        except Exception as e:
            st.error(f"오류 발생: {e}")

with connection.cursor() as cursor:
    # set dbms_cloud_ai profile(already created)
    set_profile_sql = f"""
        BEGIN
            DBMS_CLOUD_AI.set_profile(profile_name => 'OCI_GENERATIVE_AI_PROFILE');
        END;
        """
    try:
        cursor.execute(set_profile_sql)
    except oracledb.DatabaseError as e:
        raise

    connection.autocommit = True

# tokenizer
tokenizer = LlamaTokenizerFast.from_pretrained("hf-internal-testing/llama-tokenizer")
tokenizer.model_max_length = sys.maxsize

# Streamlit UI 설정
#st.set_page_config(page_title="늑대와 함께 칼춤 Season")
#st.image("assets/season_dalle.webp", caption="")
st.title("🤔 마케팅 보고서 AI Chatbot 🐺")
st.text("안녕하세요. FAQ 챗봇입니다. 아직은 견습입니다. 실수가 있더라도 이해해주세요. 😘")
st.text("example1 : 2023년 이후 가장 많은 신규 유저가 유입된 마케팅 활동을 찾아서 전체 내용을 정리해줘.")
st.text("example2 : 2023년 이후 가장 많은 탈퇴 유저가 발생한 마케팅 활동을 찾아서 전체 내용을 정리해줘.")
# 채팅 입력창
user_input = st.text_input("무엇이 궁금하신가요?") + "(결과에 마케팅 진행일자, 마케팅 예산, ROI, 주요 결과 KPI 및 주요 마케팅 전략을 포함)"
st.text("endpoint : " + endpoint)
if st.button("전송") and user_input:

    # ADB query for vector search
    results = vector_search(connection, encoder, user_input, sql)

    select_ai_sql = f"""narrate {user_input}"""
    
    results_select_ai = select_ai(connection, select_ai_sql)

    log_text_area("1. 질문을 벡터로 변환후 ADB에서 Vector 유사도 검색 결과 :", results, 200)
    
     # transform docs into a string array using the "paylod" key
    docs_as_one_string = "\n=========\n".join([doc[1]["text"] for doc in results])
    log_text_area("docs_as_one_string  :", docs_as_one_string, 200)
    
    docs_truncated = truncate_string(docs_as_one_string, 1000)

    log_text_area("2. LLM 프롬프팅에 추가하기 위해 검색 결과 전처리 :", docs_truncated, 200)
    
    prompt = f"""\
        <s>[INST] <<SYS>>
        너의 이름은 "울프 마케터"야.
        너는 사용자에게 "늑대와 함께 칼춤"이라는 게임의 마케팅 보고서 정보를 안내해주는 챗봇이야. 
        사용자에게 답변할 때는 오직 'vector_search_results'나 'select_ai_results' 중 하나의 정보만 사용해서 응답해줘.
        'vector_search_results', 'select_ai_results'의 내용 중 질문에 가장 적절한 내용을 한 가지만 사용해.
        질문이 'vector_search_results', 'select_ai_results'의 내용과 연관성이 없다면 답변을 거부해.
        우선적으로 Markdown언어로 응답을 만들어줘.
        사용자는 게임 마케팅 부서의 담당자들이야.
        <</SYS>>[/INST]

        [INST]
        이 질문에 간략하게 응답해줘 : {user_input},  반드시 'vector_search_results', 'select_ai_results' 중 가장 적절한 한 가지 내용만을 사용해서 응답해.
        'vector_search_results', 'select_ai_results' 자체에 대해서는 답변을 하지마.
        잘 모르는 질문에 대해서는 아래와 같이 응답해줘.
        "질문한 내용은 제가 잘 모르겠어요. ㅜ.ㅜ;;".
        =====
        vector_search_results: {docs_truncated}
        select_ai_results : {results_select_ai}
        =====
        응답할 때 다음을 유의해서 응답해.
        1. 3문단 이하로 응답할 것
        2. 마케팅 진행일자, 마케팅 예산, ROI, 주요 결과 KPI 및 주요 마케팅 전략을 각각 최대 50자 이내로 요약 정리할 것
        3. 2번의 내용 중에 확인할 수 없는 내용은 '확인 필요'로 응답할 것
        4. 90%의 간결성(spartan)을 가질 것
        5. 마케팅 전문가의 대화 스타일을 사용할 것
        [/INST]
        """

    prompt_audit = f"""\
        <s>{docs_truncated}
        
        위의 내용은 {user_input}이라는 질문에 대한 답이야. 내용 중 질문과 연관성이 있는지 내용이 포함되어 있다면 '1', 아니라면 '0'으로 답해줘.
        그리고 다음줄에 그 이유를 50자 이내로 간략하게 설명해줘.
        """

    prompt_suggest = f"""\
        <s>{docs_truncated}
        
        위의 내용은 {user_input}이라는 질문에 대해 Vector 유사성 검색을 통한 결과야.
        연관성이 없는 결과가 검색이 되었다면 질문을 어떻게 물어보면 좋을지 제안해줘.
        그리고 그 이유를 50자 이내로 간략하게 설명해줘.
        """
    
    log_text_area("3. 벡터 검색 결과를 포함한 프롬프트 :", prompt, 200)
    
    with st.spinner("울프 마케터 챗봇이 응답 생성 중..."):
        try:
            response = get_cohere_response(prompt)
            st.text_area("울프 마케터:", response, height=200)
            response = get_cohere_response(prompt_audit)
            st.text_area("답변 검증:", response, height=200)
            response = get_cohere_response(prompt_suggest)
            st.text_area("수정 제안:", response, height=200)
        except Exception as e:
            st.error(f"오류 발생: {e}")
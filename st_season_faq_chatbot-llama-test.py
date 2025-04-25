import json
import oracledb
import oci
import array 
import streamlit as st
from sentence_transformers import SentenceTransformer

# SentenceTransformer로 인코더 설정 (한국어 텍스트에 적합한 모델 사용)
encoder = SentenceTransformer('jhgan/ko-sroberta-multitask')

# OCI connection 설정
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

# Service endpoint 설정 (수정됨)
endpoint = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"

# GenAI client 설정
generative_ai_inference_client = oci.generative_ai_inference.GenerativeAiInferenceClient(
    config=config, service_endpoint=endpoint, 
    retry_strategy=oci.retry.NoneRetryStrategy(), timeout=(10, 240)
)

# Llama 70B 모델 ID 설정 (수정됨)
model_id = "meta.llama-3.1-70b-instruct"  # Llama 70B 모델 ID로 수정

# ADB Query 설정 (vector search)
topK = 2
table_name = 'kdww_season_faqs_embv2'
sql = f"""select payload, vector_distance(vector, :vector, COSINE) as score
from {table_name}
order by score
fetch approx first {topK} rows only"""

# OCI Generative AI API 호출 함수
def get_llama_response(prompt):
    # API 요청 객체 생성
    content = oci.generative_ai_inference.models.TextContent()
    content.text = prompt

    message = oci.generative_ai_inference.models.Message()
    message.role = "USER"
    message.content = [content]

    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    chat_request.messages = [message]
    chat_request.max_tokens = 600
    chat_request.temperature = 1
    chat_request.frequency_penalty = 0
    chat_request.presence_penalty = 0
    chat_request.top_p = 0.75
    chat_request.top_k = -1

    chat_detail = oci.generative_ai_inference.models.ChatDetails()
    chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(model_id=model_id)  # Llama 70B 모델 ID
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = compartment_id

    # 실제 API 요청 호출
    chat_response = generative_ai_inference_client.chat(chat_detail)

    # 응답에서 메시지 반환
    return chat_response.data.chat_response.choices[0].message.content[0].text
    
# 벡터 검색 함수
def vector_search(connection, user_input, sql):
    with connection.cursor() as cursor:
        # SentenceTransformer로 벡터 생성
        embedding = list(encoder.encode(user_input))
        vector = array.array("f", embedding)
        
        results = []
        for (info, score,) in cursor.execute(sql, vector=vector):
            text_content = info.read()
            results.append((score, json.loads(text_content)))
        
        return results

# Streamlit UI 설정
st.image("assets/seasons_gr_30.png", caption="meta.llama-3.1-70b-instruct")
st.title("🤔 늑대와 함께 칼춤 AI Chatbot 🐺")
st.text("안녕하세요. FAQ 챗봇입니다. 아직은 견습입니다. 실수가 있더라도 이해해주세요. 😘")
user_input = st.text_input("무엇이 궁금하신가요?")
st.text("endpoint : " + endpoint)
if st.button("전송") and user_input:

    # ADB query for vector search
    results = vector_search(connection, user_input, sql)

    # docs_as_one_string 생성
    docs_as_one_string = "\n=========\n".join([doc[1]["text"] for doc in results])

    docs_truncated = docs_as_one_string[:1000]  # 제한 길이

    prompt = f"""\
        <s>[INST] <<SYS>>
        너의 이름은 "울프 댄서"야.
        너는 사용자에게 "늑대와 함께 칼춤"이라는 게임의 FAQ 정보를 안내해주는 챗봇이야. 
        게임 제목의 "늑대"는 동물을 말하는 게 아닌 게임캐릭터를 비유적인 단어로 사용한거야.
        "늑대와 함께 칼춤" 게임과 너를 제외한 다른 질문에 대해서는 너는 모른다고 답변해.
        사용자에게 답변할 때는 오직 '늑대와함께칼춤FAQ'에 있는 내용만을 사용해서 응답해줘.
        질문이 '늑대와함께칼춤FAQ'의 내용에 연관성이 없다면 답변을 거부해.
        우선적으로 Markdown언어로 응답을 만들어줘.
        사용자는 "늑대와함께칼춤" 게임을 플레이하는 게이머야.
        <</SYS>> [/INST]
    
        [INST]
        이 질문에 간략하게 응답해줘 : {user_input},  반드시 '늑대와함께칼춤FAQ에 있는 내용만 사용해서 응답해.
        모르는 내용에 대해서는 "미안해! 질문한 내용은 내가 잘 모르겠어."라고 대답해.
        '늑대와함께칼춤FAQ' 자체에 대해서는 답변을 하지마.
        잘 모르는 질문에 대해서는 아래와 같이 응답해줘.
        "질문한 내용은 내가 잘 몰르지만  함께 칼춤에 대한 질문이라면 언제든 알려줄게!^^".
        =====
        늑대와함께칼춤FAQ: {docs_truncated}
        =====
        응답할 때 다음을 유의해서 응답해.
        1. 3문단 이하로 응답할 것
        2. 최대 100자 이내일 것
        3. 90%의 간결성(spartan)을 가질 것
        4. 친구인 것 처럼 편한 말로 이야기 할 것
        [/INST]
        """

    with st.spinner("울프 댄서 챗봇이 응답 생성 중..."):
        try:
            # Llama 70B 모델을 사용하여 응답 생성
            response = get_llama_response(prompt)
            st.text_area("울프 댄서:", response, height=200)
        except Exception as e:
            st.error(f"오류 발생: {e}")

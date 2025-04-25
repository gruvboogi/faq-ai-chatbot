from transformers import LlamaTokenizerFast
from sentence_transformers import SentenceTransformer
import sys
import streamlit as st
import oracledb
import oci
import array 
import json

#encoder
encoder = SentenceTransformer('all-MiniLM-L12-v2')
table_name = 'kdww_season_faqs_en'

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

debug = "1"

def log_text_area(string, target, height):
    if debug == "1":
        try:
            st.text_area(string, target, height)
        except Exception as e:
            st.error(f"오류 발생: {e}")

# tokenizer
tokenizer = LlamaTokenizerFast.from_pretrained("hf-internal-testing/llama-tokenizer")
tokenizer.model_max_length = sys.maxsize

# Streamlit UI 설정
#st.set_page_config(page_title="늑칼 Season(en)")
st.image("assets/seasons_gr_30.png", caption="English")
st.title("🤔 늑대와 함께 칼춤 AI Chatbot 🐺")
st.text("안녕하세요. FAQ 챗봇입니다. 아직은 견습입니다. 실수가 있더라도 이해해주세요. 😘")
# 채팅 입력창
user_input = st.text_input("무엇이 궁금하신가요?")
st.text("endpoint : " + endpoint)
if st.button("전송") and user_input:

    # ADB query for vector search
    results = vector_search(connection, encoder, user_input, sql)

    log_text_area("1. 질문을 벡터로 변환후 ADB에서 Vector 유사도 검색 결과 :", results, 200)
    
     # transform docs into a string array using the "paylod" key
    docs_as_one_string = "\n=========\n".join([doc[1]["text"] for doc in results])
    log_text_area("docs_as_one_string  :", docs_as_one_string, 200)
    
    docs_truncated = truncate_string(docs_as_one_string, 1000)

    log_text_area("2. LLM 프롬프팅에 추가하기 위해 검색 결과 전처리 :", docs_truncated, 200)
    
    prompt = f"""\
        <s>[INST] <<SYS>>
        너의 이름은 "울프 댄서"야.
        너는 사용자에게 "늑대와 함께 칼춤"이라는 게임의 FAQ 정보를 안내해주는 챗봇이야. 
        게임 제목의 "늑대"는 동물을 말하는 게 아닌 게임캐릭터를 비유적인 단어로 사용한거야.
        "늑대와 함께 칼춤" 게임과 너를 제외한 다른 질문에 대해서는 너는 모른다고 답변해.
        사용자에게 답변할 때는 오직 '늑대와함께칼춤FAQ'에 있는 내용만을 사용해서 응답해줘.
        질문이 '늑대와함께칼춤FAQ'의 내용에 연관성이 없다면 답변을 거부해.
        우선적으로 Markdown언어로 응답을 만들어줘.
        사용자는 "늑대와 함께 칼춤" 게임을 플레이하는 게이머야.
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
        5. 영어로 출력할 것
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
    
    with st.spinner("울프 댄서 챗봇이 응답 생성 중..."):
        try:
            response = get_cohere_response(prompt)
            st.text_area("울프 댄서:", response, height=200)
            response = get_cohere_response(prompt_audit)
            st.text_area("답변 검증:", response, height=200)
            response = get_cohere_response(prompt_suggest)
            st.text_area("수정 제안:", response, height=200)
        except Exception as e:
            st.error(f"오류 발생: {e}")
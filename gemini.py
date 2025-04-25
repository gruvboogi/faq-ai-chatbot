import json
from google import genai

with open("api_config.json", "r") as f:
    variables = json.load(f)

client = genai.Client(api_key=variables["gemini_api_key"])

response = client.models.generate_content(
    model="gemini-2.0-flash", contents="Explain how Oracle Gen AI works in a few words"
)
print(response.text)

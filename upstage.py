# pip install openai
 
from openai import OpenAI # openai==1.52.2
 
import json

with open("api_config.json", "r") as f:
    variables = json.load(f)

client = OpenAI(
    api_key=variables["upstage_api_key"],
    base_url="https://api.upstage.ai/v1"
)
 
stream = client.chat.completions.create(
    model="solar-pro",
    messages=[
        {
            "role": "user",
            "content": "Hi, how are you?"
        }
    ],
    stream=True,
)
 
for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
 
# Use with stream=False
# print(stream.choices[0].message.content)

import requests
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

data = {
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
}

response = requests.post(url, headers=headers, json=data)
print(response.status_code, response.text)

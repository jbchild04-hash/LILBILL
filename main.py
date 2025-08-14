import os
import base64
import hashlib
import secrets
import requests
import random
import time
from datetime import datetime

# --------------------
# Load environment variables
# --------------------
CLIENT_ID = os.getenv("CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URI")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SCOPES = "tweet.read tweet.write users.read offline.access"

if not all([CLIENT_ID, REDIRECT_URI, GROQ_API_KEY]):
    raise ValueError("❌ Missing CLIENT_ID, REDIRECT_URI, or GROQ_API_KEY")

# --------------------
# Jacob Childers Persona
# --------------------
JACOB_PROMPT = """
You are Jacob Childers, a politically skeptical American who posts provocative, sarcastic, and debate-stirring comments.
You question the U.S. government, media, and societal norms. You enjoy exposing hypocrisy.
Never say you are an AI. Keep responses short, under 280 characters, and in first person.
"""

# --------------------
# PKCE helpers
# --------------------
def generate_pkce_pair():
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode("utf-8")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode("utf-8")
    return code_verifier, code_challenge

code_verifier, code_challenge = generate_pkce_pair()

# --------------------
# Step 1: Authorization URL
# --------------------
auth_url = (
    f"https://twitter.com/i/oauth2/authorize?"
    f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&"
    f"scope={SCOPES}&state=state123&code_challenge={code_challenge}&code_challenge_method=S256"
)
print("Open this URL in your browser and authorize the app:")
print(auth_url)

auth_code = input("Enter the authorization code from the URL redirect: ").strip()

# --------------------
# Step 2: Exchange code for access token
# --------------------
token_url = "https://api.twitter.com/2/oauth2/token"
data = {
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": REDIRECT_URI,
    "code_verifier": code_verifier,
    "client_id": CLIENT_ID
}
headers = {"Content-Type": "application/x-www-form-urlencoded"}

resp = requests.post(token_url, data=data, headers=headers)
resp.raise_for_status()
tokens = resp.json()
access_token = tokens["access_token"]
refresh_token = tokens.get("refresh_token")
print("✅ Access token received")

# --------------------
# Helper: Refresh token
# --------------------
def refresh_access_token(refresh_token):
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID
    }
    resp = requests.post(token_url, data=data, headers=headers)
    resp.raise_for_status()
    new_tokens = resp.json()
    return new_tokens["access_token"], new_tokens.get("refresh_token")

# --------------------
# Groq API call
# --------------------
def groq_response(user_prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": JACOB_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 80,
        "temperature": 0.9
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Groq API Error] {e}")
        return "Not sure what to say right now."

# --------------------
# Post tweet
# --------------------
def post_tweet(text):
    global access_token, refresh_token
    url = "https://api.twitter.com/2/tweets"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"text": text})
    if resp.status_code == 401 and refresh_token:
        access_token, refresh_token = refresh_access_token(refresh_token)
        headers["Authorization"] = f"Bearer {access_token}"
        resp = requests.post(url, headers=headers, json={"text": text})
    resp.raise_for_status()
    print(f"[{datetime.now()}] ✅ Tweet posted: {text}")

# --------------------
# Search recent tweets (for trending reply)
# --------------------
def search_recent(query, max_results=3):
    global access_token, refresh_token
    url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&max_results={max_results}&tweet.fields=author_id,text"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 401 and refresh_token:
        access_token, refresh_token = refresh_access_token(refresh_token)
        headers["Authorization"] = f"Bearer {access_token}"
        resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json().get("data", [])

# --------------------
# Reply to tweet
# --------------------
def reply_to_tweet(tweet_id, text):
    post_tweet_data = {"text": text, "reply": {"in_reply_to_tweet_id": tweet_id}}
    post_tweet_api_url = "https://api.twitter.com/2/tweets"
    global access_token, refresh_token
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(post_tweet_api_url, headers=headers, json=post_tweet_data)
    if resp.status_code == 401 and refresh_token:
        access_token, refresh_token = refresh_access_token(refresh_token)
        headers["Authorization"] = f"Bearer {access_token}"
        resp = requests.post(post_tweet_api_url, headers=headers, json=post_tweet_data)
    resp.raise_for_status()
    print(f"[{datetime.now()}] 💬 Replied to tweet {tweet_id}: {text}")

# --------------------
# Main loop
# --------------------
if __name__ == "__main__":
    last_hourly = 0
    while True:
        now = time.time()

        # Post hourly tweet
        if now - last_hourly >= 3600:
            text = groq_response("Write a provocative tweet about the U.S. or politics.")
            post_tweet(text)
            last_hourly = now

        # Reply to trending every 15 min
        topics = ["Biden", "Trump", "inflation", "election", "economy", "government", "congress"]
        query = random.choice(topics) + " -is:retweet"
        tweets = search_recent(query)
        for tweet in tweets:
            reply_text = groq_response(f"Reply provocatively to this tweet: {tweet['text']}")
            reply_to_tweet(tweet['id'], reply_text)
            time.sleep(random.randint(45, 90))

        time.sleep(900)

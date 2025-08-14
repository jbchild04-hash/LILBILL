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
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")  # optional for first-time setup
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
# PKCE helpers for first-time authorization
# --------------------
def generate_pkce_pair():
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode("utf-8")
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b'=').decode("utf-8")
    return code_verifier, code_challenge

def first_time_authorization():
    """Run this function locally to get refresh token once"""
    code_verifier, code_challenge = generate_pkce_pair()
    auth_url = (
        f"https://twitter.com/i/oauth2/authorize?"
        f"response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&"
        f"scope={SCOPES}&state=state123&code_challenge={code_challenge}&code_challenge_method=S256"
    )
    print("Open this URL in your browser and authorize the app:")
    print(auth_url)
    auth_code = input("Enter the authorization code from the redirect URL: ").strip()

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
    print("\n✅ Access token:", tokens["access_token"])
    print("✅ Refresh token (use this in Railway env):", tokens["refresh_token"])
    return tokens["access_token"], tokens["refresh_token"]

# --------------------
# Token management
# --------------------
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

def refresh_access_token():
    """Get new access token using stored refresh token"""
    global REFRESH_TOKEN
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    resp = requests.post(TOKEN_URL, data=data, headers=headers)
    resp.raise_for_status()
    tokens = resp.json()
    REFRESH_TOKEN = tokens.get("refresh_token", REFRESH_TOKEN)
    return tokens["access_token"]

# --------------------
# Initialize access token
# --------------------
if REFRESH_TOKEN:
    access_token = refresh_access_token()
else:
    print("⚠️ No REFRESH_TOKEN found. Run first_time_authorization() locally to get it.")
    access_token, REFRESH_TOKEN = first_time_authorization()
    print("\n💡 Add the REFRESH_TOKEN to your Railway environment variables for future runs.")

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

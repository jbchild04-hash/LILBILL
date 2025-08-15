import os
import time
import tweepy
import requests
import random
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

CLIENT_ID = os.getenv("TWITTER_CLIENT_ID")
CLIENT_SECRET = os.getenv("TWITTER_CLIENT_SECRET")
REDIRECT_URI = os.getenv("TWITTER_REDIRECT_URI", "http://127.0.0.1:8080/callback")
REFRESH_TOKEN = os.getenv("TWITTER_REFRESH_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

JACOB_PROMPT = "You are Jacob Childers, a provocative, skeptical political commentator who posts short, ragebait remarks."

def groq_response(user_prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
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
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Groq API Error] {e}")
        return "Not sure what to say right now."

# ---- Local server to catch Twitter's redirect ----
class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global REFRESH_TOKEN
        if "code=" in self.path:
            code = self.path.split("code=")[1].split("&")[0]
            print(f"✅ Received OAuth code: {code}")

            auth = tweepy.OAuth2UserHandler(
                client_id=CLIENT_ID,
                redirect_uri=REDIRECT_URI,
                scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
                client_secret=CLIENT_SECRET
            )
            token_data = auth.fetch_token(code=code)
            REFRESH_TOKEN = token_data.get("refresh_token")

            print(f"✅ Got refresh token: {REFRESH_TOKEN}")
            print("⚠️ Add this refresh token to Railway Variables as TWITTER_REFRESH_TOKEN")

            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful! You can close this window.</h1>")

            threading.Thread(target=shutdown_server, daemon=True).start()

def shutdown_server():
    time.sleep(1)
    os._exit(0)

def run_oauth_server(auth_url):
    print(f"🌐 Please visit this URL to authorize:\n{auth_url}")
    print("Waiting for redirect to complete...")
    HTTPServer(("0.0.0.0", 8080), OAuthHandler).serve_forever()

# ---- Twitter API setup ----
def get_api():
    global REFRESH_TOKEN

    auth = tweepy.OAuth2UserHandler(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        scope=["tweet.read", "tweet.write", "users.read", "offline.access"],
        client_secret=CLIENT_SECRET
    )

    if not REFRESH_TOKEN:
        auth_url = auth.get_authorization_url()
        run_oauth_server(auth_url)

    token_data = auth.refresh_token(
        "https://api.twitter.com/2/oauth2/token",
        refresh_token=REFRESH_TOKEN
    )
    return tweepy.Client(token_data["access_token"])

# ---- Bot actions ----
def post_hourly_tweet(client):
    tweet_text = groq_response("Write a provocative tweet about the U.S. or politics.")
    try:
        client.create_tweet(text=tweet_text)
        print(f"[{datetime.now()}] ✅ Posted hourly tweet: {tweet_text}")
    except Exception as e:
        print(f"[Hourly Tweet Error] {e}")

def reply_to_trending(client):
    topics = ["Biden", "Trump", "inflation", "election", "economy", "government", "congress"]
    query = random.choice(topics) + " lang:en -is:retweet"
    try:
        tweets = client.search_recent_tweets(query=query, max_results=5)
        if not tweets.data:
            return
        for tweet in tweets.data:
            reply_text = groq_response(f"Reply provocatively to this tweet: {tweet.text}")
            client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
            print(f"[{datetime.now()}] 💬 Replied to tweet ID {tweet.id}: {reply_text}")
            time.sleep(random.randint(45, 90))
    except Exception as e:
        print(f"[Trending Reply Error] {e}")

if __name__ == "__main__":
    client = get_api()
    last_hourly = 0
    while True:
        now = time.time()
        if now - last_hourly >= 3600:
            post_hourly_tweet(client)
            last_hourly = now
        reply_to_trending(client)
        time.sleep(900)
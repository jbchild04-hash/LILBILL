import os
import time
import tweepy
import requests
import random
from datetime import datetime

# --------------------
# Load environment variables
# --------------------
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --------------------
# Verify environment variables
# --------------------
missing_vars = [v for v in ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_SECRET", "GROQ_API_KEY"]
                if not os.getenv(v)]
if missing_vars:
    raise ValueError(f"❌ Missing environment variables: {', '.join(missing_vars)}")

print("✅ All environment variables found.")

# --------------------
# Twitter authentication using Tweepy Client
# --------------------
try:
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET,
        wait_on_rate_limit=True
    )
    user = client.get_me()
    twitter_username = user.data.username
    print(f"✅ Twitter authentication successful. Logged in as @{twitter_username}")
except Exception as e:
    print(f"❌ Twitter authentication failed: {e}")
    client = None  # Prevent main loop from crashing

# --------------------
# Jacob Childers Persona
# --------------------
JACOB_PROMPT = """
You are Jacob Childers, a politically skeptical American who posts provocative, sarcastic, and debate-stirring comments.
You question the U.S. government, media, and societal norms. You enjoy exposing hypocrisy.
Never say you are an AI. Keep responses short, under 280 characters, and in first person.
"""

# --------------------
# Groq API call
# --------------------
def groq_response(user_prompt):
    if not GROQ_API_KEY:
        print("❌ Groq API key missing.")
        return "Not sure what to say right now."
    
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
    except requests.HTTPError as http_err:
        print(f"[Groq API HTTP Error] {http_err} | Response: {response.text}")
        return "Not sure what to say right now."
    except Exception as e:
        print(f"[Groq API Error] {e}")
        return "Not sure what to say right now."

# --------------------
# Post hourly tweet
# --------------------
def post_hourly_tweet():
    if not client:
        print("❌ Skipping hourly tweet because Twitter auth failed.")
        return
    tweet_text = groq_response("Write a provocative tweet about the U.S. or politics.")
    try:
        client.create_tweet(text=tweet_text)
        print(f"[{datetime.now()}] ✅ Posted hourly tweet: {tweet_text}")
    except Exception as e:
        print(f"[Hourly Tweet Error] {e}")

# --------------------
# Reply to trending tweets
# --------------------
def reply_to_trending():
    if not client:
        print("❌ Skipping trending replies because Twitter auth failed.")
        return
    topics = ["Biden", "Trump", "inflation", "election", "economy", "government", "congress"]
    query = random.choice(topics) + " -is:retweet"

    try:
        tweets = client.search_recent_tweets(query=query, max_results=3, tweet_fields=["author_id"])
        if not tweets.data:
            return
        for tweet in tweets.data:
            if str(tweet.author_id) == user.data.id:
                continue  # skip own tweets
            reply_text = groq_response(f"Reply provocatively to this tweet: {tweet.text}")
            client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
            print(f"[{datetime.now()}] 💬 Replied to tweet ID {tweet.id}: {reply_text}")
            time.sleep(random.randint(45, 90))
    except Exception as e:
        print(f"[Trending Reply Error] {e}")

# --------------------
# Main loop
# --------------------
if __name__ == "__main__":
    last_hourly = 0
    while True:
        now = time.time()

        # Post hourly
        if now - last_hourly >= 3600:
            post_hourly_tweet()
            last_hourly = now

        # Reply to trending every 15 minutes
        reply_to_trending()

        time.sleep(900)  # Wait 15 min before checking again

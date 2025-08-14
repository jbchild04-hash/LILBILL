import os
import requests
import random
from datetime import datetime
import tweepy

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
# Twitter authentication (read-only, free tier)
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
    client = None

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
    except Exception as e:
        print(f"[Groq API Error] {e}")
        return "Not sure what to say right now."

# --------------------
# Free-tier safe functions
# --------------------
def fetch_recent_tweets(topic="Trump"):
    """Fetch recent tweets only (cannot post or reply)"""
    if not client:
        print("❌ Skipping fetch because Twitter auth failed.")
        return
    query = topic + " -is:retweet"
    try:
        tweets = client.search_recent_tweets(query=query, max_results=5)
        if tweets.data:
            for tweet in tweets.data:
                print(f"[{datetime.now()}] 📰 {tweet.text}")
        else:
            print("No recent tweets found.")
    except Exception as e:
        print(f"[Fetch Error] {e}")

# --------------------
# Main loop (read-only)
# --------------------
if __name__ == "__main__":
    topics = ["Biden", "Trump", "inflation", "election", "economy"]
    while True:
        topic = random.choice(topics)
        fetch_recent_tweets(topic)
        # Wait 15 min before checking again
        import time
        time.sleep(900)
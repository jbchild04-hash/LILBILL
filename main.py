import os
import time
import tweepy
import requests
import random
from datetime import datetime

# --------------------
# Load environment variables from Railway
# --------------------
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --------------------
# Check that all variables exist
# --------------------
missing_vars = [v for v in ["API_KEY", "API_SECRET", "ACCESS_TOKEN", "ACCESS_SECRET", "GROQ_API_KEY"]
                if not os.getenv(v)]
if missing_vars:
    raise ValueError(f"❌ Missing environment variables: {', '.join(missing_vars)}")

# --------------------
# Authenticate with Twitter
# --------------------
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True)

# --------------------
# Jacob Childers Persona
# --------------------
JACOB_PROMPT = """
You are Jacob Childers, a politically skeptical American who posts provocative, sarcastic, and debate-stirring comments.
You question the U.S. government, media, and societal norms. You enjoy exposing hypocrisy.
Never say you are an AI. Keep responses short, under 280 characters, and in first person.
"""

def groq_response(user_prompt):
    """Generate a Jacob Childers-style tweet or reply using Groq's LLaMA 3 model"""
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
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Groq API Error] {e}")
        return "Not sure what to say right now."

def post_hourly_tweet():
    """Post a ragebait-style tweet once an hour"""
    tweet_text = groq_response("Write a provocative tweet about the U.S. or politics.")
    try:
        api.update_status(tweet_text)
        print(f"[{datetime.now()}] ✅ Posted hourly tweet: {tweet_text}")
    except Exception as e:
        print(f"[Hourly Tweet Error] {e}")

def reply_to_trending():
    """Reply to trending tweets in politics/news"""
    topics = ["Biden", "Trump", "inflation", "election", "economy", "government", "congress"]
    query = random.choice(topics) + " -filter:retweets"

    try:
        tweets = api.search_tweets(q=query, count=3, lang="en", result_type="popular")
        for tweet in tweets:
            if tweet.user.screen_name.lower() != api.me().screen_name.lower():
                reply_text = groq_response(f"Reply provocatively to this tweet: {tweet.text}")
                api.update_status(
                    status=f"@{tweet.user.screen_name} {reply_text}",
                    in_reply_to_status_id=tweet.id
                )
                print(f"[{datetime.now()}] 💬 Replied to @{tweet.user.screen_name}: {reply_text}")
                time.sleep(random.randint(45, 90))  # Delay to avoid spam
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

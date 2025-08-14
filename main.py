import tweepy
import openai
import os
import time
from dotenv import load_dotenv
from flask import Flask
import threading
import random

load_dotenv()

# -------------------
# API Keys
# -------------------
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Twitter & OpenAI auth
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth, wait_on_rate_limit=True)
openai.api_key = OPENAI_KEY

# -------------------
# Persona
# -------------------
PERSONA_PROMPT = """You are Jacob Childers, a 28-year-old news commentator in the U.S. in 2025. 
You provide sarcastic, witty commentary on current events and news. You're skeptical of politicians 
and institutions, but you base your opinions on facts. Your tone is casual, sarcastic, and sometimes 
cynical, but you avoid personal attacks and stick to critiquing policies and public actions. 
Keep responses under 270 characters for Twitter. Be factual but with a sharp, sarcastic edge."""

# -------------------
# Timers & tracking
# -------------------
last_hour_post = 0
last_engage = 0
last_mentions = 0
replied_ids = set()

# Sample news topics for commentary
NEWS_TOPICS = [
    "breaking news",
    "politics today",
    "economic news",
    "technology news",
    "government policy",
    "current events"
]

# -------------------
# OpenAI helper
# -------------------
def gpt_reply(prompt_text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Changed from gpt-4o-mini for broader compatibility
            messages=[
                {"role": "system", "content": PERSONA_PROMPT},
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=100,
            temperature=0.8
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI error: {e}")
        return "Sorry, having technical difficulties with my wit today. 🤖"

# -------------------
# Bot actions
# -------------------
def hourly_post():
    global last_hour_post
    if time.time() - last_hour_post >= 3600:  # Every hour
        topic = random.choice(NEWS_TOPICS)
        prompt = f"Write a sarcastic commentary tweet about {topic} in the style of Jacob Childers. Keep it factual but witty, under 270 characters."
        try:
            tweet = gpt_reply(prompt)
            # Ensure tweet isn't too long
            if len(tweet) > 280:
                tweet = tweet[:277] + "..."
            
            api.update_status(tweet)
            print(f"[Hourly Post] {tweet}")
        except Exception as e:
            print(f"Error posting hourly tweet: {e}")
        
        last_hour_post = time.time()

def reply_to_mentions():
    global last_mentions
    if time.time() - last_mentions >= 300:  # Every 5 minutes
        try:
            mentions = api.mentions_timeline(count=5, tweet_mode='extended')
            for mention in reversed(mentions):
                if mention.id not in replied_ids:
                    # Clean the mention text
                    text = mention.full_text.replace(f"@{api.verify_credentials().screen_name}", "").strip()
                    
                    if text:  # Only reply if there's actual content
                        prompt = f"Someone mentioned you with: '{text}'. Respond as Jacob Childers with witty commentary, under 250 characters."
                        reply = gpt_reply(prompt)
                        
                        # Ensure reply isn't too long (accounting for @username)
                        max_length = 280 - len(f"@{mention.user.screen_name} ")
                        if len(reply) > max_length:
                            reply = reply[:max_length-3] + "..."
                        
                        api.update_status(
                            status=f"@{mention.user.screen_name} {reply}",
                            in_reply_to_status_id=mention.id
                        )
                        print(f"[Reply] @{mention.user.screen_name}: {reply}")
                        replied_ids.add(mention.id)
                        
                        # Limit to 1 reply per cycle to avoid spam
                        break
                        
        except Exception as e:
            print(f"Error in reply_to_mentions: {e}")
        
        last_mentions = time.time()

def engage_with_trending():
    global last_engage
    if time.time() - last_engage >= 7200:  # Every 2 hours (reduced frequency)
        try:
            # Search for recent tweets about news/politics
            search_terms = ["news", "politics", "breaking", "government"]
            search_query = random.choice(search_terms)
            
            tweets = api.search_tweets(
                q=f"{search_query} -rt",  # Exclude retweets
                count=5,
                result_type="recent",
                lang="en"
            )
            
            for tweet in tweets:
                # Only engage with tweets that have some engagement but aren't super viral
                if 5 <= (tweet.favorite_count + tweet.retweet_count) <= 100:
                    prompt = f"Write a brief sarcastic comment about this tweet: '{tweet.text}'. Stay factual but witty, under 250 characters."
                    reply = gpt_reply(prompt)
                    
                    try:
                        # Ensure reply isn't too long
                        max_length = 280 - len(f"@{tweet.user.screen_name} ")
                        if len(reply) > max_length:
                            reply = reply[:max_length-3] + "..."
                            
                        api.update_status(
                            status=f"@{tweet.user.screen_name} {reply}",
                            in_reply_to_status_id=tweet.id
                        )
                        print(f"[Trending Reply] {reply}")
                        # Only do one engagement per cycle
                        break
                    except Exception as e:
                        print(f"Error replying to trending tweet: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error in engage_with_trending: {e}")
        
        last_engage = time.time()

# -------------------
# Main loop
# -------------------
def run_bot():
    print("LILBILL Bot (Jacob Childers) starting up...")
    
    # Test API connection
    try:
        user = api.verify_credentials()
        print(f"Connected as: @{user.screen_name}")
    except Exception as e:
        print(f"Twitter API connection failed: {e}")
        return
    
    while True:
        try:
            hourly_post()
            reply_to_mentions()
            engage_with_trending()
            time.sleep(60)  # Check every minute
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

# -------------------
# Flask keep-alive for Railway
# -------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "LILBILL (Jacob Childers) Commentary Bot is running! 🤖"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "LILBILL", "persona": "Jacob Childers"}

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# Start server and bot
if __name__ == "__main__":
    # Start Flask server in background
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Run the bot in main thread
    run_bot()

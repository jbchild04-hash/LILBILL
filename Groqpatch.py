import os
from dotenv import load_dotenv

load_dotenv()  # Only if you have a .env file
print(os.getenv("GROQ_API_KEY"))   # Should print your key
print(os.getenv("TWITTER_API_KEY"))  # Should print your key

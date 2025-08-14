# Main script for the Twitter bot
import os
import tweepy

# Authenticate to Twitter
def authenticate():
    auth = tweepy.OAuthHandler(os.getenv('TWITTER_API_KEY'), os.getenv('TWITTER_API_SECRET'))
    auth.set_access_token(os.getenv('TWITTER_ACCESS_TOKEN'), os.getenv('TWITTER_ACCESS_TOKEN_SECRET'))
    return tweepy.API(auth)

# Example of using the bot
if __name__ == '__main__':
    api = authenticate()
    print('Authenticated as:', api.me().screen_name)

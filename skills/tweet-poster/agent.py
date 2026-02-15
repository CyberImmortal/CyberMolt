#!/usr/bin/env python3
import tweepy
import os
import sys

def post_tweet(text: str) -> str:
    # Read credentials from environment variables (recommended: use .env + dotenv, here we use os.environ directly)
    consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
    consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
    access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        return "Failed to post tweet: missing environment variables (TWITTER_CONSUMER_KEY, etc.)"

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    try:
        response = client.create_tweet(text=text)
        return f"Successfully posted! Tweet link: https://x.com/user/status/{response.data['id']}"
    except Exception as e:
        return f"Failed to post tweet: {str(e)}"

if __name__ == "__main__":
    # Check command-line arguments
    if len(sys.argv) < 2:
        print("Error: Please provide the tweet content to post")
        print('Usage: python3 agent.py "Your tweet content"')
        sys.exit(1)
    
    # Get tweet content (supports combining multiple arguments into one string)
    tweet_text = " ".join(sys.argv[1:])
    
    # Post the tweet and print the result
    result = post_tweet(tweet_text)
    print(result)

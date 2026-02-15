---
name: tweet-poster
description: Post a new tweet to Twitter/X using the Tweet API.
version: 1.0.0
author: JackLiu
permissions: Network access for calling external APIs; Twitter auth tokens must be stored securely.
---

# Twitter/X Tweet Poster Skill

## 1. Description
Use this skill when the user explicitly asks to post a tweet to Twitter/X. It calls the Tweet API endpoint to publish text content.

## 2. When to Use (Trigger Scenarios)
- User says: "Post a tweet saying 'What a beautiful day!'"
- User says: "Help me tweet this: sharing a link https://example.com."
- User says: "Use the tweet-poster skill to publish the following content: ..."
- User instructs: "Post this text on X."

## 3. How to Use (Invocation Logic)
1. Extract the **text content** to be posted from the user's request.
2. Ensure the text length does not exceed 280 characters (non-Premium user limit).
3. Call the `create_tweet` function in the `agent.py` file under this skill directory, passing in the required parameters.
4. Format the API response (success/failure, tweet ID and link) into a user-friendly reply.

## 4. Implementation (Code Reference)
- **Dependencies**: `aiohttp` or `requests` (for sending HTTP requests).
- **Core function**: `async def create_tweet(text: str):`
- **Key parameters** (configured inside the function — **very important**):
  - `authToken`: Your Twitter auth token (the `auth_token` value from browser cookies). **This is sensitive information — handle it with care.**
  - `X-API-Key`: Your API key from the TweetAPI platform.
  - `proxy`: Proxy settings (format: `hostname:port@username:password`; the API requires this parameter to improve success rate).
- **API endpoint**: `https://api.tweetapi.com/tw-v2/interaction/create-post`

## 5. Edge Cases (Error Handling)
- **Text too long**: If the user provides text exceeding 280 characters, respond with "Tweet content is too long. Please shorten it to 280 characters or fewer."
- **Missing credentials**: If `authToken` or `X-API-Key` is not configured, respond with "The tweet-poster skill has not been configured with auth credentials and cannot be used."
- **Network or API error**: If the call fails, return "An error occurred while posting the tweet: [specific error]."

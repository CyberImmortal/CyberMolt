import requests
import json
import argparse
import os
import sys
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tweepy

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# DashScope OpenAI-compatible endpoint
DEFAULT_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CHAT_COMPLETIONS_PATH = "/chat/completions"

DEFAULT_MODEL = "qwen-max"
REPLY_MIN_LEN = 30
REPLY_MAX_LEN = 180
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # Exponential backoff base (seconds)

# config.json path: same directory as agent.py
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

# ---------------------------------------------------------------------------
# Configuration Loading
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load configuration from config.json in the same directory as agent.py."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to read {CONFIG_PATH}: {e}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("cybermolt")


def setup_logging(verbose: bool = False) -> None:
    """Configure logging level and format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Prompt Construction
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = "You are a helpful assistant that strictly follows instructions."

REPLY_PROMPT_TEMPLATE = """\
You are a sharp, insightful commenter on X (Twitter). Your job is to write a \
high-quality reply that adds genuine value to the conversation. You are NOT \
promoting anything — you are simply an engaged, knowledgeable participant.

Original tweet author: @{author}
Original tweet content:
{tweet_content}

Follow these rules strictly (output the final reply text only, no explanations):

1. **Relevance first**: Your reply must directly engage with the original tweet's \
topic. Reference a specific point, add a new angle, share a concise insight, or \
respectfully challenge an idea. Never be generic.

2. **Add value**: Provide one of the following — a fresh perspective, a concise \
counterpoint, a related fact, a thought-provoking question, or a brief personal \
take. The reader should feel smarter or more curious after reading your reply.

3. **Tone**: Conversational, witty when appropriate, confident but not arrogant. \
Sound like a well-read person casually sharing thoughts — not a bot, not a \
marketer, not a fanboy.

4. **Absolute no-go**:
   - NO self-promotion, links, donation addresses, or project shilling
   - NO hashtags unless the original tweet already uses them and it feels natural
   - NO "check out", "follow me", "support us" or any call-to-action
   - NO generic praise like "Great post!", "So true!", "Love this!"
   - NO emojis overuse — at most 1 emoji, and only if it fits naturally
   - NO filler words or padding to inflate length

5. **Format**:
   - Length: {min_len}-{max_len} characters
   - Language: match the original tweet's language exactly
   - Each generation must vary in structure and vocabulary — never repeat patterns
   - Do NOT start with @{author} unless it adds conversational value

Output one reply. Nothing else.
"""


def build_prompt(tweet_content: str, author: str) -> str:
    """Build the user prompt based on tweet content and author."""
    return REPLY_PROMPT_TEMPLATE.format(
        tweet_content=tweet_content,
        author=author,
        min_len=REPLY_MIN_LEN,
        max_len=REPLY_MAX_LEN,
    )


# ---------------------------------------------------------------------------
# API Call & Retry
# ---------------------------------------------------------------------------
@dataclass
class GenerateResult:
    """Wrapper for the generation result, making it easy for callers to check success/failure."""
    success: bool
    reply: str = ""
    error: str = ""
    length_warning: str = ""


def _call_api(
    prompt: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    api_base: str = DEFAULT_API_BASE,
    temperature: float = 0.75,
    top_p: float = 0.85,
    max_tokens: int = 1024,
    timeout: int = 30,
) -> str:
    """
    Call the DashScope OpenAI-compatible API and return the model output text.

    Raises:
        requests.exceptions.RequestException: Network/HTTP errors
        ValueError: Unexpected response format
    """
    url = f"{api_base.rstrip('/')}{CHAT_COMPLETIONS_PATH}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
    }

    logger.debug("POST %s  model=%s", url, model)
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    response.raise_for_status()
    result = response.json()

    # Parse OpenAI-compatible format
    choices = result.get("choices")
    if choices and isinstance(choices, list) and len(choices) > 0:
        content = choices[0].get("message", {}).get("content", "")
        if content:
            return content.strip()

    # Fallback: DashScope native format (in case the API returns the legacy format)
    output = result.get("output", {})
    if "choices" in output and output["choices"]:
        return output["choices"][0]["message"]["content"].strip()
    if "text" in output:
        return output["text"].strip()

    raise ValueError(f"Failed to extract content from API response: {json.dumps(result, ensure_ascii=False)[:300]}")


def generate_reply(
    tweet_content: str,
    api_key: str,
    author: str = "cz_binance",
    model: str = DEFAULT_MODEL,
    api_base: str = DEFAULT_API_BASE,
    max_retries: int = MAX_RETRIES,
) -> GenerateResult:
    """
    Generate a reply to the given tweet content using the Qwen API, with exponential backoff retry.

    Args:
        tweet_content: Original tweet content
        api_key: DashScope API Key
        author: Original tweet author username (e.g. cz_binance, heyibinance)
        model: Model name
        api_base: API base URL
        max_retries: Maximum number of retries

    Returns:
        GenerateResult object
    """
    if not tweet_content or not tweet_content.strip():
        return GenerateResult(success=False, error="Tweet content cannot be empty")
    if not api_key:
        return GenerateResult(success=False, error="API Key cannot be empty")
    if not author or not author.strip():
        return GenerateResult(success=False, error="Author username cannot be empty")

    # Strip any manually added @ prefix
    author = author.strip().lstrip("@")

    prompt = build_prompt(tweet_content.strip(), author=author)
    last_error = ""

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Attempt %d/%d to generate reply (model=%s)", attempt, max_retries, model)
            reply_text = _call_api(prompt, api_key, model=model, api_base=api_base)

            # Length validation
            length_warning = ""
            reply_len = len(reply_text)
            if reply_len < REPLY_MIN_LEN:
                length_warning = f"Reply length ({reply_len}) is below the recommended minimum ({REPLY_MIN_LEN})"
                logger.warning(length_warning)
            elif reply_len > REPLY_MAX_LEN:
                length_warning = f"Reply length ({reply_len}) exceeds the recommended maximum ({REPLY_MAX_LEN})"
                logger.warning(length_warning)

            logger.info("Successfully generated reply (length=%d)", reply_len)
            return GenerateResult(success=True, reply=reply_text, length_warning=length_warning)

        except requests.exceptions.RequestException as e:
            last_error = f"API request failed: {e}"
            logger.warning("Attempt %d request failed: %s", attempt, last_error)
        except ValueError as e:
            last_error = f"Response parsing failed: {e}"
            logger.warning("Attempt %d parsing failed: %s", attempt, last_error)
        except Exception as e:
            last_error = f"Unknown error: {e}"
            logger.error("Attempt %d exception: %s", attempt, last_error)

        if attempt < max_retries:
            wait = RETRY_BACKOFF_BASE ** attempt
            logger.info("Waiting %d seconds before retrying...", wait)
            time.sleep(wait)

    return GenerateResult(success=False, error=f"Failed after {max_retries} retries. Last error: {last_error}")


# ---------------------------------------------------------------------------
# Reply to Tweet via Twitter API
# ---------------------------------------------------------------------------
def post_reply(tweet_id: str, reply_text: str) -> str:
    """
    Post a reply to the specified tweet using Twitter API v2.

    Reads credentials from environment variables:
        TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET,
        TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET

    Args:
        tweet_id: The ID of the tweet to reply to.
        reply_text: The reply content to post.

    Returns:
        A message indicating success (with tweet link) or failure.
    """
    consumer_key = os.environ.get("TWITTER_CONSUMER_KEY")
    consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET")

    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        return (
            "Failed to post reply: missing Twitter environment variables "
            "(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, "
            "TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)"
        )

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    try:
        response = client.create_tweet(
            text=reply_text,
            in_reply_to_tweet_id=tweet_id,
        )
        return (
            f"Successfully replied! Tweet link: "
            f"https://x.com/user/status/{response.data['id']}"
        )
    except Exception as e:
        return f"Failed to post reply: {str(e)}"


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="CyberMolt Reply Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python agent.py -t "AI is going to replace a lot of jobs" -a cz_binance\n'
            '  python agent.py -t "Welcome to the Binance ecosystem" -a heyibinance --model qwen-plus\n'
            '  python agent.py -t "Some tweet" -a cz_binance -tid 1234567890 -r true\n'
        ),
    )

    parser.add_argument(
        "-t", "--tweet",
        type=str,
        required=True,
        help="The tweet content to reply to",
    )
    parser.add_argument(
        "-a", "--author",
        type=str,
        required=True,
        help="Original tweet author username (e.g. cz_binance, heyibinance)",
    )
    parser.add_argument(
        "-tid", "--tweet-id",
        type=str,
        default=None,
        help="The tweet ID to reply to (required when -r is set to true)",
    )
    parser.add_argument(
        "-r", "--reply",
        type=str,
        default="false",
        choices=["true", "false"],
        help="Set to 'true' to directly post the reply to the tweet (default: false)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Qwen model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (output to stderr)",
    )

    args = parser.parse_args()

    # Only enable logging in verbose mode, otherwise stay silent
    if args.verbose:
        setup_logging(verbose=True)

    should_reply = args.reply.lower() == "true"

    # Validate: -r true requires -tid
    if should_reply and not args.tweet_id:
        print(
            "Error: -tid/--tweet-id is required when -r is set to true",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load config: config.json > environment variables
    config = load_config()
    api_key = config.get("DASHSCOPE_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("Error: API Key not found. Please set DASHSCOPE_API_KEY in config.json", file=sys.stderr)
        sys.exit(1)

    tweet_content = args.tweet.strip()
    if not tweet_content:
        print("Error: Tweet content cannot be empty", file=sys.stderr)
        sys.exit(1)

    author = args.author.strip().lstrip("@")
    if not author:
        print("Error: Author username cannot be empty", file=sys.stderr)
        sys.exit(1)

    result = generate_reply(tweet_content, api_key, author=author, model=args.model)

    if result.success:
        # Output the raw reply text
        print(result.reply)

        # If -r true, post the reply directly to the tweet
        if should_reply:
            logger.info("Posting reply to tweet %s ...", args.tweet_id)
            post_result = post_reply(args.tweet_id, result.reply)
            print(post_result)
    else:
        print(f"Generation failed: {result.error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

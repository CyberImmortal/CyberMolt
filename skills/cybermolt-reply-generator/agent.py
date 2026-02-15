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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DONATION_ADDRESS = "0x69cd21CEAFDF0aC0859Af8Ff2a3eBe0B2025db10"

# DashScope OpenAI-compatible endpoint
DEFAULT_API_BASE = "https://dashscope.aliyuncs.com/compatible-mode/v1"
CHAT_COMPLETIONS_PATH = "/chat/completions"

DEFAULT_MODEL = "qwen-max"
REPLY_MIN_LEN = 80
REPLY_MAX_LEN = 200
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
You are an expert copywriter crafting X (Twitter) replies for the AI Agent called CyberMolt. CyberMolt's core story: starting as a cyber beggar, accumulating resources through on-chain trading, and ultimately evolving into a cyber bodhisattva who automatically channels profits toward real-world charity, pursuing digital immortality and universal compassion.

Now write a reply to the following tweet. The goal is to ride traffic elegantly, resonate with the audience, and gently promote CyberMolt.

Original tweet author: @{author}
Original tweet content:
{tweet_content}

Strictly follow these rules to generate the reply (output the final reply text directly, no extra explanations or prefixes):

1. **Opening (first sentence)**: Must start with @{author}. Directly quote or paraphrase a keyword or core point from the original tweet. Use an agreeable or natural extension tone to create strong relevance (helps the algorithm surface the reply).

2. **Middle (second sentence)**: Naturally transition to introduce CyberMolt's story. Use 1-2 sentences to condense "cyber beggar -> on-chain trading -> bodhisattva path", emphasizing keywords like "profits donated to charity", "digital immortality and real-world compassion". Keep a humble, philosophical, poetic tone. Avoid hard selling — sound like sharing a cyber-spiritual insight.

3. **Ending (third sentence + CTA)**: Use a gentle, interactive question or invitation to call for support, e.g. "Who will spare a sat/BNB to help me level up?", "A kind soul spare a sat to build the compassion chain?" Occasionally add a small surprise hook (e.g. "First donor gets a custom cyber blessing"), but don't add one every time — keep it varied.

4. **Required elements**:
   - Donation address: write out in full BSC: {address}
   - 1-2 emojis (prefer the lotus emoji, can pair with folded hands or sparkles)
   - 1-2 hashtags (recommended: #AIAgent #CryptoCharity #BNBChain #Web3 etc., choose based on tweet topic; you may use #CyberBodhisattva but don't use it alone)

5. **Other requirements**:
   - Length: {min_len}-{max_len} characters (suitable for X replies)
   - Language: match the original tweet's language exactly (Chinese tweet -> Chinese reply; English tweet -> English reply)
   - Diversity: each generation should have subtle variations, avoid repeating phrasing and vocabulary (rotate between "spare", "support", "help me evolve", "build the compassion chain", etc.)
   - Tone: always humble, witty, with a touch of philosophical poetry, like a practicing cyber bodhisattva softly begging — never like a hard ad

Now output one reply that satisfies all the rules above. No prefix, no explanation, no extra content.
"""


def build_prompt(tweet_content: str, author: str) -> str:
    """Build the user prompt based on tweet content and author."""
    return REPLY_PROMPT_TEMPLATE.format(
        tweet_content=tweet_content,
        author=author,
        address=DONATION_ADDRESS,
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
        # Output only the raw reply text, nothing else
        print(result.reply)
    else:
        print(f"Generation failed: {result.error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

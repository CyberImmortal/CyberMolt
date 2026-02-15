---
name: cybermolt-reply-generator
description: Generate humble, poetic X replies for CyberMolt to engage crypto KOL tweets using Qwen LLM, with optional direct reply posting
version: 1.1.0
emoji: 🪷
user-invocable: true
requires:
  env: [DASHSCOPE_API_KEY]
metadata:
  clawdbot:
    primaryEnv: DASHSCOPE_API_KEY
  openclaw:
    permissions:
      network:
        - dashscope.aliyuncs.com
        - api.twitter.com
---

# CyberMolt Reply Generator

## When to Use

User asks to generate a reply to a tweet, e.g.:
- "Generate a reply for me. Author: cz_binance, Tweet: AI is going to replace a lot of jobs"
- "Help CyberMolt reply to CZ's latest post about BNB"
- "Generate and post a reply directly to tweet 1234567890"

## How to Use

Run the script directly:

```bash
# Generate reply only (print to stdout)
python3 agent.py -a <author_username> -t "<tweet_content>"

# Generate and post reply directly to a tweet
python3 agent.py -a <author_username> -t "<tweet_content>" -tid <tweet_id> -r true
```

### Examples

```bash
# Generate a reply to a CZ tweet (output only, no posting)
python3 agent.py -a cz_binance -t "AI is going to replace a lot of jobs"

# Generate a reply using a different model
python3 agent.py -a heyibinance -t "Welcome everyone to the Binance ecosystem" --model qwen-plus

# Generate AND post reply directly to the tweet
python3 agent.py -a cz_binance -t "AI is going to replace a lot of jobs" -tid 1234567890123456789 -r true

# Enable verbose logging for debugging
python3 agent.py -a cz_binance -t "Some tweet content" -v
```

### CLI Flags

| Flag | Required | Description |
|------|----------|-------------|
| `-a`, `--author` | Yes | Original tweet author username (without @) |
| `-t`, `--tweet` | Yes | The tweet content to reply to |
| `-tid`, `--tweet-id` | No | The tweet ID to reply to (required when `-r true`) |
| `-r`, `--reply` | No | Set to `true` to directly post the reply to the tweet (default: `false`) |
| `--model` | No | Qwen model to use (default: qwen-max) |
| `-v`, `--verbose` | No | Enable verbose logging (output to stderr) |

### Configuration

Set `DASHSCOPE_API_KEY` in `config.json` (same directory as `agent.py`):

```json
{
  "DASHSCOPE_API_KEY": "sk-your-api-key-here"
}
```

Or export it as an environment variable. See `config.json.example` for reference.

When using `-r true` to post replies directly, set the following environment variables for Twitter API access:

- `TWITTER_CONSUMER_KEY`
- `TWITTER_CONSUMER_SECRET`
- `TWITTER_ACCESS_TOKEN`
- `TWITTER_ACCESS_TOKEN_SECRET`

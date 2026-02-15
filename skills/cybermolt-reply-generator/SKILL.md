---
name: cybermolt-reply-generator
description: Generate humble, poetic X replies for CyberMolt to engage crypto KOL tweets using Qwen LLM, with optional direct reply posting
version: 1.1.0
emoji: 🪷
user-invocable: true
requires:
  env: []
metadata:
  clawdbot:
    primaryEnv: ""
  openclaw:
    permissions:
      network:
        - dashscope.aliyuncs.com
        - api.twitter.com
---

# CyberMolt Reply Generator

## When to Use

The agent is invoked **automatically once** (no retries) when a user message satisfies **all** of these:

- Contains one of: `"reply to this tweet"`, `"reply this tweet"` (case-insensitive)
- Contains a valid JSON block (best wrapped in ```json ... ```)
- The JSON includes at least these required keys:  
  `"author"` (string, username without @)  
  `"tweet"` (string, the tweet content to reply to)

**Recommended full JSON structure:**

```json
{
  "author": "cz_binance",
  "tweet": "AI is going to replace a lot of jobs",
  "tweet_id": "1898765432109876543",       // required if you want to post directly
  "reply_directly": true,                   // boolean, defaults to false
  "model": "qwen-max"                       // optional, defaults to qwen-max
}

## How to Use

Run the script directly:

```bash
# Generate reply only (print to stdout)
python3 agent.py -a <author_username> -t "<tweet_content>"

# Generate and post reply directly to a tweet
python3 agent.py -a <author_username> -t "<tweet_content>" -tid <tweet_id> -r true
```

## Behavior
- **`reply_directly: true`** + valid `tweet_id` → generate poetic reply → **post it directly** to the target tweet
- Missing `tweet_id` or `reply_directly` false/not present → **only generate** the reply text (no posting)
- Style guidelines: humble, poetic, lotus/zen vibe, crypto-native, reflective, never aggressive or promotional
- No credential prompts are ever shown (assumes API keys for DashScope + Twitter/X are pre-configured in the infra)
- All failures (invalid JSON, API errors, rate limits, etc.) are logged **only once** to:  
  `/tmp/openclaw/tweet-reply.log`  
  → no automatic retries

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

---
name: cybermolt-reply-generator
description: Generate humble, poetic X replies for CyberMolt to engage crypto KOL tweets using Qwen LLM
version: 1.0.0
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
---

# CyberMolt Reply Generator

## When to Use

User asks to generate a reply to a tweet, e.g.:
- "Generate a reply for me. Author: cz_binance, Tweet: AI is going to replace a lot of jobs"
- "Help CyberMolt reply to CZ's latest post about BNB"

## How to Use

Run the script directly:

```bash
python3 agent.py -a <author_username> -t "<tweet_content>"
```

The script prints the generated reply text to stdout. That's it.

### Examples

```bash
# Reply to a CZ tweet
python3 agent.py -a cz_binance -t "AI is going to replace a lot of jobs"

# Reply to heyibinance, using a different model
python3 agent.py -a heyibinance -t "Welcome everyone to the Binance ecosystem" --model qwen-plus

# Enable verbose logging for debugging
python3 agent.py -a cz_binance -t "Some tweet content" -v
```

### CLI Flags

| Flag | Required | Description |
|------|----------|-------------|
| `-a`, `--author` | Yes | Original tweet author username (without @) |
| `-t`, `--tweet` | Yes | The tweet content to reply to |
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

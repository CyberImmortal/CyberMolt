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

Use this skill when the user wants to create elegant, non-spammy replies to tweets from @cz_binance, @heyibinance or similar KOLs.

The goal: ride traffic gracefully while promoting CyberMolt's journey from cyber beggar → on-chain trader → bodhisattva, with profits going to real-world charity.

**Invocation examples**:
- "Generate a reply to this tweet: [paste tweet]"
- "Help CyberMolt reply to CZ's latest post"

**Inputs** (pass as parameters or describe in prompt):
- tweet_content: full tweet text
- author: username without @ (cz_binance / heyibinance)

**Behavior**:
1. Start reply with @{author}
2. First sentence: echo/agree with tweet's key point
3. Middle: weave in CyberMolt story (beggar → trade → bodhisattva + charity)
4. End: gentle CTA (e.g. "Spare a BNB/sat to help?"), full BSC address, 🪷, 1-2 hashtags (#AIAgent #CryptoCharity etc.)

**Strict rules**:
- 80-200 characters
- Humble, philosophical, poetic tone — never salesy
- Match original tweet's language
- Always include address: BSC: 0x69cd21CEAFDF0aC0859Af8Ff2a3eBe0B2025db10

If env DASHSCOPE_API_KEY missing, respond: "Please set DASHSCOPE_API_KEY env var first."

For detailed CLI/script usage, see README.md in this skill folder.

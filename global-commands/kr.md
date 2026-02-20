---
description: Toggle Korean language mode — Haiku translates input, Claude responds in Korean
allowed-tools: Bash
---

# /kr — Korean Language Mode (한국어 모드)

Toggle Korean language mode on or off.

**How it works:**
- Your Korean input is translated to English by Haiku before the main model sees it
- The main model reasons in English (efficient) and responds in Korean natively
- No translation overhead on the main model — just a language switch on output
- Haiku handles the translation at ~10x lower cost than Sonnet/Opus

Run this Bash command to toggle the flag and report status:

```bash
FLAG="$HOME/.claude/korean_mode"
if [ -f "$FLAG" ]; then
  rm "$FLAG"
  echo "✓ Korean mode DISABLED"
  echo "Claude will respond in English (default)"
else
  touch "$FLAG"
  echo "✓ Korean mode ENABLED — 한국어 모드가 활성화되었습니다"
  echo "Claude will now respond in Korean. Your Korean input will be translated to English by Haiku for efficient processing."
fi
```

After toggling, confirm to the user in the appropriate language whether Korean mode is now on or off.

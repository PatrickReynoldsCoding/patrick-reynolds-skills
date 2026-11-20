---
name: text-me
description: Send a push notification to Patrick's Android phone through ntfy. Use on /text-me, or when Patrick says "ping me", "text me", "notify me when done" or "let me know on my phone". `/text-me <message>` sends that message; with no message, send a short "done" note.
argument-hint: "[message]"
---

# Text me

Send one push notification to Patrick's phone with ntfy.

## Steps
1. **Check the topic is set.** The topic name is a secret. It lives in the environment variable `NTFY_TOPIC` on Patrick's Mac, never in this repo.
   ```bash
   [ -n "$NTFY_TOPIC" ] && echo set || echo missing
   ```
   If it prints `missing`, stop and tell Patrick to add `export NTFY_TOPIC=<topic>` to `~/.zshenv`. Do not guess a topic.
2. **Pick the message.** Use the argument if there is one. Otherwise use a short note such as `Claude is done`.
   - Keep it generic and short. Do not put repo names, ticket text, customer names or other private details in it. ntfy.sh is a public service.
3. **Send it.**
   ```bash
   curl -fsS -H "Title: Claude" -d "<message>" "ntfy.sh/$NTFY_TOPIC"
   ```
4. **Confirm in one line** ("Sent."). If `curl` fails, show the error. Never print the topic.

## Rules
- Never write the topic into a file, commit, log or reply.
- Send one notification per request. Do not loop.

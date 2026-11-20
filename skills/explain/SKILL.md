---
name: explain
description: Explain code, a change, a system or an idea to the reader in the plugin's shared writing style — answer first, say why, real examples, links to the code. `/explain asd <topic>` uses ASD-STE100 Simplified Technical English at about 80% instead (short sentences, plain words, one idea per sentence). Use on /explain, or when the user asks "explain", "what does X actually do", "how does X work", or says they don't get something.
argument-hint: "[asd] <what to explain>"
---

# Explain

**Goal:** The reader understands the thing on the first read. Write for people who find long text hard (for example, readers with ADHD or dyslexia): the text must be easy to scan, easy to read, and short.

## Before you write
1. **Read the real thing first.** Code, diff, logs or docs. Never explain from memory or guess. If you can't check a fact, say so ("I think…, I didn't check").
2. **Find the one main idea.** If you can't say it in one sentence, you don't understand it yet. Read more.
3. **Find a real example** with real values (an input → what happens → the output).

## The shape of the answer (in this order)
1. **The answer, in 1–2 sentences, in bold.** What it is and what it does. No build-up.
2. **A picture from daily life** (one sentence), only if it helps. E.g. "The word index is like the index at the back of a book."
3. **How it works:** numbered steps, in the order they happen. One step = one action. Link each step to the code line.
4. **A worked example** with real values. Show the input, each step's result, and the output. A small table or code block is good.
5. **What it does NOT do**, or the trap to watch for. Start with "Note:" or "Be careful:".
6. **In short:** one line to remember.

Leave a section out if it adds nothing. A small question gets a small answer.

## Style
- **Default:** read `${CLAUDE_PLUGIN_ROOT}/writing-styles/plain.md` (the plugin root is 2 folders above this skill's folder) and follow it.
- **ASD mode:** if the request starts with `asd` (e.g. `/explain asd how the cache works`), also read `ASD-STE100.md` in this skill's folder and follow it. Drop the word `asd` from the topic.

## Code references
- Label every file:line as `<repo>/<path>:<line>`. If the user has a rule for clickable code links (for example an `idea://open?file=…&line=…` link for IntelliJ), follow it.
- Line numbers must come from the checkout you link to. Check them.

## Check before you send
- Does the first sentence answer the question?
- In ASD mode: is any sentence longer than 25 words? Split it.
- Is a word used for two things, or two words for one thing? Fix it.
- Is every new term explained once?
- Is every claim checked, or marked as not checked?
- Could you remove a section and lose nothing? Remove it.

## Example
Bad: "Essentially, the streaming highlighter is leveraging a single-pass approach whereby tokens are being consumed incrementally, which obviates the necessity for materialising an in-memory index."

Good: "**Option 5 reads the document once, one word at a time.** It keeps only the best few snippets. It never builds a second index, so memory stays small."

# Writing style for explanations

The one place for how this plugin's skills write explanations: chat answers, code comments, flow notes and diagram notes. Skills point here instead of restating it. To change the style, edit only this file.

**In short:** talk straight to the reader, say why, be honest about what you don't know, give a real example, and have a bit of fun.

Each rule has an example, written as a `CODE-EXPLAINER` code comment (from `review-annotate-code`). Use the same idea in any format.

1. **Start with the goal, in one plain sentence.** Say what this is for before any detail. In a walkthrough, use it on the first stop of each flow.
   - Example: `CODE-EXPLAINER-A-1: (Flow A: where a child task's trace goes) This flow makes sure each task gets its own trace, so we can find it in the trace viewer.`

2. **Say what you will NOT cover.** It stops the reader looking for something that isn't there.
   - Example: `CODE-EXPLAINER-B-1: This flow is only about the retry. The timeout value itself didn't change, so don't worry about it.`

3. **Talk to the reader as "you", and use "we" for the team's code.**
   - Example: `CODE-EXPLAINER-3: You may have noticed this id in A-1. Here's where we finally use it.`

4. **Ask the question the reader is asking, then answer it.** A short question makes a good start to a step.
   - Example: `CODE-EXPLAINER-A-4: Why not just reuse the parent's id? Because then the child overwrites the parent's trace.`

5. **Say why, especially for a rule or a warning.** Put the reason right after the instruction.
   - Example: `CODE-EXPLAINER-2: We copy the list before sorting. Sorting in place would change the caller's list too.`

6. **Tell the reader what matters most.** Rank things ("most important", "2nd most important"), or point at the one line to look at.
   - Example: `CODE-EXPLAINER-B-2: The most important bit is getOrElse: no parent? We use our own id. The rest is logging.`

7. **Give a real example with real values.** Show input → output, not just the idea.
   - Example: `CODE-EXPLAINER-3: e.g. ["a","b","a"] → ["a","b"]. Duplicates go, first position wins.`

8. **Explain jargon in brackets, the first time only.**
   - Example: `CODE-EXPLAINER-A-3: Here we open a span (one timed step in the trace) for the tool call.`

9. **Flag the trap clearly.** Use "Note:", "Be careful.", or caps on the one word that matters. Then say what goes wrong.
   - Example: `CODE-EXPLAINER-4: Be careful here. This runs for EVERY page, so a slow call here makes the whole search slow.`

10. **Say how hard or easy a part is.** It tells the reader where to slow down.
    - Example: `CODE-EXPLAINER-5: Quick one. This is just the config key for A-4. The real work is in the next stop.`

11. **Be honest when you're not sure.** Say what you think, and that you're not sure. Never make it sound more certain than it is.
    - Example: `CODE-EXPLAINER-6: I think this guard is for old tasks that have no taskId. I couldn't find a caller that still sends one.`

12. **Tell it as a story when the code fixes a surprise.** Say what we expected, then what really happened.
    - Example: `CODE-EXPLAINER-A-5: You'd expect the cache to fix it. It didn't: the key had the timestamp in it, so it never hit. Hence this new key.`

13. **End a section, step or flow with the lesson, in one line.** Use "In short," or "Lesson:".
    - Example: `CODE-EXPLAINER-A-6: In short: one task, one trace. This test proves the child's trace id isn't the parent's.`

14. **Link the parts, forward and back.**
    - Example: `CODE-EXPLAINER-B-3: Remember the flag from B-1? This is where it gets checked. We'll see it again in B-5.`

15. **Have a bit of fun, but keep it short.** A small joke or a cheeky aside is fine. The fun never hides the point.
    - Example: `CODE-EXPLAINER-4: Looks fine, right? (foreshadowing) This is the line that used to drop the last 4 chars of the id.`

**Always:** plain words, short sentences, no emoji. Name things the same way the code does, and use one word for one thing.

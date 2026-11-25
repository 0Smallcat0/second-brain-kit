---
name: blind-three-way
description: Use before choosing a direction or plan: write your own plan to a file first and do not show it; give only the requirements and facts to the other AIs the user has (or fresh subagents) and let each propose independently; compare the three side by side, run one anonymous cross-critique if they disagree, write down differences, blind spots and trade-offs, then choose.
---

# Blind three-way

Use this when the choice is a direction, a design, a topic, a strategy or a way of doing something, not when carrying out a plan that is already decided. One mind picks the first idea it likes; three minds that have not seen each other's plan find what the first one missed.

## Steps
1. **Your plan first.** Write your own plan into a file and show it to no one. This fixes what you thought before anything influenced it.
2. **Brief the others without your plan.** Give each of them only the requirements and the facts: the goal behind the goal, the constraints, the numbers, what is already decided, what must not happen. No candidates, no hint of your leaning.
3. **Who the others are.** Other AIs the user actually has (only those; never assume an account the user did not tick at setup). If the user has only Claude: two fresh subagents that cannot see this conversation, each told to propose independently. Ask each for a concrete plan with its reasons and the biggest risk in it.
4. **Compare side by side.** Put the three plans in one table: what each chose, why, and what each ignored.
5. **If they disagree, one anonymous round.** Give each author the other two plans with the authors removed and ask for the strongest objections and the blind spots. Do not reveal whose plan is whose.
6. **Write it down, then choose.** Write the differences, the blind spots and the trade-offs, then pick, with one line of reasons. If the choice is hard to reverse or a risk is still open, say so and ask the user before going on. The user may overrule the choice; the final say is theirs.

## Keep in mind
- Anything sent to another AI leaves this computer: send only what the question needs, no personal data, and nothing to a service the user did not allow.
- Use it at the fork in the road, not at every turn: a long job should not be re-run through it for every small step.

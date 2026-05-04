# Deck review: Cursor Meetup, May 2026

## Audience perspective

The original deck had strong ingredients but opened with project vocabulary before audience pain. A meetup audience needs to know, in the first minute, why this matters to their Cursor workflow.

What changed:
- Title now says the concrete pain: "Stop re-teaching your repo to every coding agent."
- Slide 2 reframes cold start as a familiar room-level moment, not an abstract taxonomy.
- Slide 3 explains what the artifact is not: not memory, not RAG, not a hosted service.
- Slide 7 now has a visual fallback instead of a placeholder for the pre-recorded clip, so the GitHub Pages deck still works without embedded media.

## Expert technical presenter perspective

The risk was credibility whiplash: the deck showed a big historical correctness result, then immediately said the fresh rerun did not reproduce correctness lift. That can sound like retreat unless the stale-pack run is framed as a quality-gate lesson, not a stage claim.

What changed:
- The deck now leads with concrete success stories before showing aggregate numbers.
- The May rerun is framed as a freshness gate: stale structured context gets discarded, updated, and rerun.
- The final claim is operational: success is measured by reviewer grade, file opens, dead ends, and risk flags.
- Freshness is elevated from a footnote to a condition of the claim.

## DevRel perspective

The old call to action pushed tier 3 first, which is a lot to ask after a talk. For adoption, the first step should be low-risk and doable tonight.

What changed:
- Final command now uses `init --tier 1`.
- Tier 3 is positioned as the next step for repos that need routes, search scopes, and CI checks.
- The deck keeps the demo at tier 3 so the audience sees the full product surface, but the CTA starts small.

## Revised Narrative Spine

1. Coding agents are capable, but each session starts as a stranger to your repo.
2. agent-context turns repeated repo explanation into a checked-in evidence layer.
3. The same pack routes Cursor, Claude, Codex, Gemini, and OpenCode through redundant project-rule files.
4. Different agents consume context differently, so the pack supports both search-and-verify and trust-and-follow loops.
5. Demo the loop: init, agent fills the pack, verify.
6. Success stories: zero-file answer, missed invariant caught, deprecated pattern avoided, Codex 6/6.
7. Evidence: 78+ reviewer-graded answers across three repo types, zero production-risk answers in structured condition.
8. Freshness gate: stale-pack runs are maintenance failures; update, verify, and rerun before claiming current Codex/Cursor numbers.
9. Try tier 1 tonight.

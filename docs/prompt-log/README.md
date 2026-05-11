# Prompt log

The leading prompt from each Claude Code session that produces code or substantial design decisions.

## Convention

- One file per session: `YYYY-MM-DD-NNN-short-slug.md` (NNN is the session number that day)
- Contents: the opening prompt verbatim, followed by any follow-up prompts that materially changed direction
- Don't capture every back-and-forth — capture the human-in-loop checkpoints

## Why this exists

This repo is a reference for what agent-assisted development looks like in practice. The prompt log demonstrates that human-in-loop discipline applies at the development layer, mirroring how the agents themselves (built in this repo) leave human-in-loop on every procurement decision. That parallel is the Responsible-AI story.

## What not to log

- Routine refactors and trivial edits
- Anything containing confidential tender data
- Personal information about NTA staff or bidders

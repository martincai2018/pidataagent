# Syncing upstream Datus changes

This repo is a thin GitHub fork of <https://github.com/Datus-ai/Datus-agent>.
All custom code lives outside `datus/` (see `pidata/`, `scripts/`,
`docs/pidataagent/`, `pidata-requirements.txt`); the vendored `datus/`
tree is never edited locally.

The local clone is shallow (`--depth 1`). Use GitHub's server-side
merge-upstream API so you don't have to fetch the full history:

```bash
# 1. Merge upstream/main into the fork on GitHub's servers.
gh api -X POST repos/martincai2018/pidataagent/merge-upstream -f branch=main

# 2. Fetch the new fork tip, deepening enough to bridge the shallow gap.
git fetch --deepen=100 origin main
git merge --ff-only origin/main
# If ff is not possible because you have unpushed local commits, push them
# first; if you truly want to discard local state, `git reset --hard
# origin/main` after a clean tree is the alternative (never add
# --allow-unrelated-histories here — in a shallow repo it forges a bogus root).
# If --deepen=100 is ever insufficient (repo advanced very far), rerun with a
# larger N or once: git fetch --unshallow origin

# 3. Refresh the environment.
uv sync --inexact
uv pip install -r pidata-requirements.txt
uv run pytest tests/pidata -v
```

Notes:

- If `git fetch` is extremely slow on your network, retry later or use a
  GitHub proxy mirror for the fetch URL; always verify the fetched commit
  SHA against the fork tip with
  `gh api repos/martincai2018/pidataagent/branches/main --jq .commit.sha`.
  After a real merge-upstream the fork tip is a new merge commit whose SHA
  differs from upstream's main; optionally confirm the official upstream SHA
  (`gh api repos/Datus-ai/Datus-agent/branches/main --jq .commit.sha`)
  appears as a parent of that merge commit.
- If `README.md` ever conflicts, re-apply the block between
  `pidataagent:fork-banner:start/end` markers and keep the upstream body.
- Never commit `conf/agent.yml`, `.datus/`, `.env`, or `subject/` —
  upstream `.gitignore` already excludes them.
- Review upstream release notes for adapter version bumps, then update
  pins in `pidata-requirements.txt`.
- After syncing, move the marker tag:
  `git tag -f "upstream-sync-$(date +%Y-%m-%d)" origin/main`
  `git push -f origin "upstream-sync-$(date +%Y-%m-%d)"`

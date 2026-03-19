# /release — Full Release Cycle

Execute the complete release workflow for mcp-memory-service.

## Steps

### 1. List Open PRs with Status
```bash
gh pr list --state open --json number,title,labels,reviews,statusCheckRollup --template '{{range .}}#{{.number}} {{.title}} | CI: {{range .statusCheckRollup}}{{.conclusion}} {{end}}| Reviews: {{range .reviews}}{{.state}} {{end}}{{"\n"}}{{end}}'
```
Review each PR's CI status and review approvals. Report any that are blocked.

### 2. Merge Approved PRs
For each PR that has:
- All CI checks passing (green)
- At least one approved review

Merge using:
```bash
gh pr merge <number> --squash --delete-branch
```
If any PR has failing CI or pending reviews, skip it and report why.

### 3. Verify CI Green on Main
```bash
gh run list --branch main --limit 3 --json status,conclusion,name
```
If the latest run is not `success`, STOP and report the failure. Do not proceed.

### 4. Check Landing Page Version Staleness
```bash
# Get latest git tag
LATEST_TAG=$(git describe --tags --abbrev=0)
# Check version in landing page
grep -o 'v[0-9]\+\.[0-9]\+\.[0-9]\+' docs/index.html | head -1
```
If the landing page version is behind the latest tag AND this is a MINOR or MAJOR release, update `docs/index.html`:
- Version badge
- Test count (`data-target`)
- Feature cards if applicable
- Re-publish to here.now: `cd docs && ~/.agents/skills/here-now/scripts/publish.sh . --slug merry-realm-j835`

### 5. Bump Version (Semver)
Determine bump type from PR labels:
- `breaking` or `major` → MAJOR
- `enhancement` or `feature` → MINOR
- `bug`, `fix`, `security`, `dependencies` → PATCH

Invoke the `github-release-manager` agent to handle:
- Version bump in `_version.py`, `pyproject.toml`, `README.md`, `uv.lock`
- CHANGELOG.md update with all merged PR summaries
- Commit, tag, and GitHub Release with generated notes

**NEVER manually edit version files** — always use the agent.

### 6. Create Git Tag + GitHub Release
The `github-release-manager` agent handles this, but verify:
```bash
# Confirm tag exists
git tag --list 'v*' | tail -3
# Confirm GitHub release
gh release view $(git describe --tags --abbrev=0)
```

### 7. Clean Up Merged Branches
```bash
# Delete local branches that have been merged to main
git branch --merged main | grep -v '^\*\|main$' | xargs -r git branch -d
# Delete remote branches that have been merged
gh pr list --state merged --json headRefName --template '{{range .}}{{.headRefName}}{{"\n"}}{{end}}' | while read branch; do
  git push origin --delete "$branch" 2>/dev/null
done
```

### 8. Save Release Summary to MCP Memory
Store a summary of the release using MCP Memory Server:
- Version number and bump type
- PRs included with their numbers and titles
- Any issues closed
- Landing page update status
- Tags: `mcp-memory-service`, `release`, `v<VERSION>`

## Error Handling
- If CI is red: stop and report. Do not merge or release.
- If a PR merge fails: skip it, continue with others, report at end.
- If version bump fails: stop and report. Do not create partial releases.
- If landing page publish fails: continue release, note as follow-up task.

## Post-Release Verification
After all steps complete, verify:
```bash
# PyPI (triggered by tag push via GitHub Actions)
pip index versions mcp-memory-service | head -1
# GitHub release exists
gh release list --limit 1
```

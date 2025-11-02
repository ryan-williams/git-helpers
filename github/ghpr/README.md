# ghpr-py

GitHub PR/Issue management tool for local iteration with gist mirroring.

## Features

- **Clone** PR/Issues locally with comments
- **Sync** bidirectionally between GitHub and local files
- **Diff** local changes vs remote
- **Push** updates back to GitHub
- **Gist mirroring** for version control and sharing
- **Comment management** - edit and sync PR/issue comments

## Installation

```bash
pip install ghpr-py
```

## Usage

```bash
# Clone a PR or issue
ghpr clone https://github.com/owner/repo/pull/123
# or
ghpr clone owner/repo#123

# Show differences
ghpr diff

# Push changes
ghpr push

# Add a new comment
ghpr comment my-draft.md
```

## Directory Structure

Cloned issues are stored as:
```
gh/123/
  owner-repo#123.md       # Main description
  z3404494861-user.md     # Comments (ID-author format)
  z3407382913-user.md
```

## Development

Part of [git-helpers](https://github.com/ryan-williams/git-helpers).

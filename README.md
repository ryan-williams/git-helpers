# git-helpers
Git aliases and scripts.

<!-- toc -->
- [Setup](#setup)
- [Commands](#commands)
    - [Inspect commit graph](#graphs)
    - [Summarize local/remote branches](#branches)
    - [Inspect commits being rebased/cherry-picked](#gshrh)
    - [Rebase](#rebase)
        - [`gtw` (`git-throw`)](#gtw)
        - [`groc` (`git-reorder-commits`)](#groc)
        - [`grbcd` (`git-rebase-preserve-commit-dates`)](#grbcd)
    - [Diff helpers, GIFs, JSON](#diff)
    - [Update commit parents](#parents)
    - [Push repo state to remote](#copy-diffs)
<!-- /toc -->

Here's an annotated histogram of my most-used Git aliases:
```bash
history | awk '{print $2}' | grep '^g' | sort | uniq -c | sort -rn | head -n 30
#    2776 gst     # `git status -uno` (tracked files only)
#    2734 gd      # `git diff`
#    2092 ggr     # `git graph`: wrapper for `git log --graph`, with nice colorization and formatting options
#    2062 gs      # `git status`
#     626 gcam    # `git commit -am`
#     587 gp      # `git push-x`: `push` to one or more remotes (comma-delimited)
#     538 gap     # `git add -p` (add interactively, in chunks)
#     519 gcm     # `git commit -m`
#     470 gsh     # `git show`
#     463 gco     # `git checkout`
#     448 ghh     # `git help`
#     433 gb      # `git branches` (pretty-print Git branches)
#     425 gr      # `git remote -vv`
#     404 gau     # `git add -u` (restrict to already-tracked files)
#     402 gdc     # `git diff --cached` ("staged" changes only)
#     376 gf      # `git fetch-x --tags`: fetch ≥1 remotes in parallel (comma-delimited), include tags
#     370 gg      # `git graph-all` (graph all branches)
#     242 gcaan   # `git commit --amend --no-edit`: squash uncommitted changes onto HEAD commit
#     217 ggracl  # `git graph -a -c -l`: Git branch graph, displaying author and committer dates as relative times (e.g. "3 days ago")
#     208 gcp     # `git cherry-pick`
#     194 ga      # `git add`
#     192 ggp     # `git grep --recurse-submodules`
#     175 g       # `git`
#     174 gpf     # `git push -f`
#     131 ggrh    # `git graph HEAD` (Graph of HEAD commit, plus subsequent arg branches)
#     118 gl      # `git ls-files`
#     113 grb     # `git rebase`
#     111 glg     # `git log -p --follow`, restricted to paths matching a substring argument
#     109 garc    # `git-add-rebase-continue`: mark conflicted files resolved, continue rebase
```

There are over 900 possible 2-character Bash commands (`[a-z][a-z\d]`) and 30k+ 3-characters; a goal of this repo is to help me always be within a couple keystrokes of most common Git commands.

## Setup <a id="setup"></a>
Source [`.git-rc`](./.git-rc) in your `.bashrc`:
```bash
echo ". $PWD/.git-rc" >> ~/.bashrc  # Configure new shells to load `git-helpers`
. .bash-rc                          # "source" .bashrc, for immediate effect in existing shells
```
This will load all aliases, and add relevant directories to `$PATH`. `pip install -r requirements.txt` also ensures `python-dateutil` is installed available, which some scripts here require.

## Commands <a id="commands"></a>
More details about aliases/commands I use frequently:

### Inspect commit graph <a id="graphs"></a>
`ggr` (`git-graph`) and `gg` (`git-graph-all`) are my preferred ways to visualize Git branches and history.

Example output from this repo:

![](img/gg-git-helpers.png)

The first line shows that local branch `main` is checked out (`HEAD -> main`), and up to date with remote branches `gh/main` and `gl/main` (GitHub and GitLab, resp., but that's just a convention I use).

[runsascoded/.rc] shows several parallel branch lineages I maintain:

![](img/gg-rc.png)

I develop on `gh-all`, and cherry-pick commits over to `gh-server`, `gl-all`, and `gl-server`.

[git/git] shows wide merge lineages

![](img/gg-git.png)

### Summarize local/remote branches <a id="branches"></a>

`gb` (`git branches`) is an improved version of `git branch -vv`:
- Branches output in reverse-chron order of last modification (instead of alphabetically)
- Nice colors for each field
- Concise "commits ahead/behind" counts
- Abbreviated "time since last commit"

[TileDB-SOMA] example:

![gb](img/gb-tdbs.png)

`gbr` (`git-remote-branches`) is similar, but summarizes remotes' branches.

### Inspect commits being rebased/cherry-picked <a id="gshrh"></a>

- `grbh` (`git-rebase-head`) and `gch` (`git-cherry-pick-head`) print the SHA of the commit currently being rebased or cherry-picked.
- `gshrh` (`git-show-rebase-head`) and `gshch` (`git-show-cherry-pick-head`) pass that to `git show`.

### Rebase <a id="rebase"></a>

#### `gtw` ([`git-throw`]) <a id="gtw"></a>
"Throw" (squash) uncommitted changes onto an arbitrary previous commit.

<!-- `bmdf git-throw.py -- --help` -->
```bash
git-throw.py --help
# Usage: git-throw.py [OPTIONS] DST
#
#   "Throw" (squash) uncommitted changes onto an arbitrary previous commit.
#
# Options:
#   -m, --message TEXT  Optional message to use for ephemeral commit (before it
#                       is squashed onto the commit pointed to by `dst`).
#   -n, --dry-run       1x: commit changes, print rebase todo list; 2x: don't
#                       commit changes, show simulated rebase todo list
#   --help              Show this message and exit.
```

See also:
- `gtwp` (`git throw HEAD^`): squash staged changes onto the current commit's parent.
- `gtwp2` (`git throw HEAD~2`): squash staged changes onto the current commit's grandparent.

#### `groc` (`git-reorder-commits`) <a id="groc"></a>
- Reorder commits by index (0-based, counting backwards from `HEAD`)
- The rebase starts just before the largest index provided, and "picks" commits in the order provided.

Examples:

##### Swap order of last two commits
```bash
groc 0 1
```
This rebases the last **2** commits (one more than the maximum index provided, i.e. **1**), according to the plan "0 1":
- "pick" `HEAD~0` (current `HEAD`, whose rebased parent becomes `HEAD~2`)
- "pick" `HEAD~1` (originally the parent of `HEAD`, now rebased on top of the commit from the previous step)

##### `-n`: view a rebase "plan" without executing it
```bash
groc -n 0 1
# pick 3d2e3a8 `dcw="diff --cached -w"`
# pick 2d551a6 `commit -F-` aliases
```

##### `-p`: preserve commit-dates
```bash
groc -p -n 0 1
# pick 3d2e3a8 `dcw="diff --cached -w"`
# exec git reset-committer-date-rebase-head
# pick 2d551a6 `commit -F-` aliases
# exec git reset-committer-date-rebase-head
```
Here you calls to [`git-reset-committer-date-rebase-head`] inserted after each "pick"ed commit. The `rebase` `-x` flag is also directly available, this does the same as the above:

```bash
git roc -n -x 'g rcd' 0 1
# pick 3d2e3a8 `dcw="diff --cached -w"`
# exec g rcd
# pick 2d551a6 `commit -F-` aliases
# exec g rcd
```

(`g rcd` is an alias for [`git reset-committer-date-rebase-head`])

##### No-op rotations
Running it twice is a no-op (assuming there are no rebase conflicts):
```bash
groc -p 0 1  # Reverse order of last two commits
groc -p 0 1  # Reverse back, original commit SHA
```

Similarly, here's a no-op 3-rotation:
```bash
groc -p 0 2 1  # Put current HEAD before prior two commits
groc -p 0 2 1  # Repeat; current state same as `groc -p 1 0 2`
groc -p 0 2 1  # Original commit is restored (including SHA)
```

#### `grbcd` (`git-rebase-preserve-commit-dates`) <a id="grbcd"></a>
Rebase, but inject `-x git rcd` ([`git-reset-committer-date-rebase-head`]) after each commit, so that the committer-time is preserved.

- `rb <N>`: interactive rebase over the last `N` commits.
- `grd` (`git-rebase-diff`): compute most recent pre-rebase SHA (`ghblr` / `git-head-before-last-rebase`), diff that vs. current worktree.
  - Useful to ensure a rebase didn't change the final work-tree, e.g. when combining or rearranging commits.
- `gtw` (`git-throw`): squash uncommitted changes onto an arbitrary previous commit.
  - `gtwp` (`git throw HEAD^`): squash staged changes onto the previous commit.

### Diff helpers, GIFs, JSON <a id="diff"></a>
- `gdg` (`git-diff-gif.py`): create a GIF of an image at two commits, open in browser
- `gdj` (`git-diff-json.py`): diff two JSON files, after pretty-printing
- `gdc` (`git diff --cached`): show staged changes only
- `gds` (`git diff --stat`): show file/line add/remove stats

### Update commit parents <a id="parents"></a>
Create a commit with a given tree and parents:
- `gcmp` (`git-commit-multiple-parents`): takes an optional commit message (`-m`) and commit (`-b`) whose tree to use
- `gsp` (`git-set-parents`) uses the current `HEAD`s message and tree

### Author/Committer/User metadata
- `gsau` (`git-set-author`): update `HEAD` author, either from Git configs, an existing commit, or literal name/email arguments.
- `gsad` (`git-set-author-date`): update `HEAD` author date; match another commit's, or `HEAD`'s committer date.
- `gscd` (`git-set-committer-date`): update `HEAD` committer date; match another commit's, or `HEAD`'s author date.
- `gsid` (`git-set-id`), `ggsid` (`git-set-id -g`): set `user.{name,email}` configs.

### Push repo state to remote <a id="copy-diffs"></a>

`gcd` (`git copy-diffs`) pushes the state of your local repository to a "mirror" remote, preserving:
* existing branches / `HEAD` pointer, upstreams
* staged changes
* unstaged changes
* untracked (but not `.gitignore`d) files

I've been shocked to not find support for this in `git` itself, or in any other tools people have written that solve versions of this problem. Common approaches (none of which do exactly what I want, or have undesired side-effects) are:
* commit all uncommitted changes, then push to remote.
    * optionally repeatedly amend the top commit and `push -f` that.
    * I want to preserve what is committed vs. staged vs. unstaged.
* `rsync` the entire directory
    * It's important to not push `.gitignore`d files, as this will frequently contain compilation outputs and the like.
    * One approach would be to pipe e.g. the output of `git ls-files` to `rsync` in a way that `rsync` can digest.
        * This leaves out all the other state that `git` tracks; what branch you're on, what commits all branches are on, etc. I want these things copied too.

I've implemented it here in 3 steps:
1. `rsync` the entire `.git` directory
    * this gets you all branches, index state, commits, upstream info, etc.
1. `git reset --hard HEAD`
    * the first time you do step 1, you only have a `.git` directory and none of the files that `git` thinks should be there based on the contents of `.git`; this puts everything there, but blows away the uncommitted staged changes that were stored in `.git/index`.
1. `rsync` any unstaged, staged, and untracked (but not `.gitignore`d) files, as well as `.git/index`
    * at this point all files in the "mirror" repository are equal to their counterparts in the source repo, and all `.git` state is equal as well.

#### Usage

Simply create a remote using the `add-mirror-remote` command:

    $ git add-mirror-remote my-dev-box ryan@dev-box:path/to/repo

Then you can run:

    $ git copy-diffs dev-box
    $ gcd dev-box  # for short

And all local state will be pushed to the remote, **clobbering whatever was there previously**.

As a shortcut, you can set environment variable `$MIRROR_REMOTES` to a comma-seperated list of remote names for `git copy-diffs` to look for by default:

    $ export MIRROR_REMOTES=dev-box1,dev-box2
    $ git copy-diffs  # will push to the first remote named dev-box1 or dev-box2 found in your "remotes" list


[runsascoded/.rc]: https://github.com/runsascoded/.rc
[git/git]: https://github.com/git/git
[hammerlab/guacamole]: https://github.com/hammerlab/guacamole
[TileDB-SOMA]: https://github.com/TileDB-Inc/TileDB-SOMA

[`git-reset-committer-date-rebase-head`]: commit/git-reset-committer-date-rebase-head
[`git-throw`]: rebase/git-throw.py

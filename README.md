# git-helpers
[1,231](#count-completions) Git aliases and scripts.

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

## Stats <a id="stats"></a>

### Count aliases <a id="count-completions"></a>
Most aliases in this repo begin with `g` (for Git). [count-completions.sh](scripts/count-completions.sh) counts them:
<!-- `bmdf -- scripts/count-completions.sh -c` -->
```bash
scripts/count-completions.sh -c
# 1231 completions added by installing git-helpers
# By length:
# - 2 chars: 15
# - 3 chars: 221
# - 4 chars: 455
```

A goal of this repo is to help me always be within a couple keystrokes of most common Git commands.

Here's a full list of the aliases and scripts provided by `source`ing [`.git-rc`](.git-rc):

<!-- `bmdfff -- scripts/count-completions.sh -v` -->
<details><summary><code>scripts/count-completions.sh -v</code></summary>

```
1231 new completions:
clone_org.py
copy-diffs-script
g
g1
g1f
ga
ga.
gaN
gaafp
gaapf
gaapfu
gab
gabd
gabt
gabu
gac
gacm
gacpc
gad
gadi1
gaf
gafp
gagi
gah
gamr
gan
gap
gap.
gapf
gapfu
gaps
gapu
gapu.
gar
garc
garcn
garn
gau
gau.
gauf
gaup
gaup.
gaus
gaut
gb
gbD
gbb
gbc
gbcag
gbcbb
gbd
gbdf
gbe
gbeb
gbf
gbfc
gbh
gbhi
gbhis
gbhs
gbk
gblg
gbls
gbmv
gbp
gbpa
gbpar
gbr
gbrg
gbrh
gbrm
gbrr
gbrs
gbru
gbruc
gbs
gbsb
gbsg
gbsh
gbsl
gbsn
gbsr
gbss
gbssr
gbsx
gbu
gby
gc
gca
gcaa
gcaam
gcaan
gcaane
gcaap
gcaapm
gcae
gcaem
gcam
gcamt
gcamtf
gcan
gcane
gcanea
gcap
gcapm
gcarb
gcb
gcbh
gcbn
gcbns
gccd
gcd
gcdi1
gce
gcf
gcfa
gcfd
gcfda
gcfef
gcfi
gcfia
gcfig
gcfis
gcfl
gcfn
gcfns
gcfp
gcfs
gcft
gcfu
gcfua
gcg
gcga
gcgd
gcgda
gcgef
gcgi
gcgia
gcgig
gcgis
gcgl
gcgs
gcgu
gcgua
gchf
gci
gciv
gcl
gclb
gcln
gcm
gcmab
gcmb
gcmf
gcmfa
gcmp
gcmt
gcmtf
gcmtr
gcmtrr
gcn
gcne
gcnm
gco
gco-
gcob
gcoco
gcococ
gcoct
gcoctc
gcof
gcoh
gcom
gcon
gcoo
gcop
gcor
gcorb
gcorf
gcot
gcp
gcp1
gcp2
gcpa
gcpam
gcpau
gcpc
gcph
gcpm
gcpn
gcpp
gcppa
gcppam
gcppcd
gcppm
gcps
gcpsh
gcrb
gcrbh
gcrh
gcs3
gcsb
gcsp
gct
gctg
gctgs
gctp
gctr
gd
gd-
gda
gdas
gdb
gdbr
gdbt
gdbu
gdc
gdc-
gdcno
gdcp
gdcs
gdcss
gdcw
gdcw-
gdd
gddf
gdf
gdfm
gdfr
gdft
gdg
gdgif
gdh
gdh1
gdh2
gdir
gdj
gdl
gdma
gdmb
gdmbr
gdn
gdno
gdnoa
gdnoc
gdnom
gdns
gdp
gdp1
gdp2
gdph
gdps
gdq
gdr
gdrb
gds
gds1
gdsc
gdsca
gdsd
gdsh
gdsl
gdsp
gdsph
gdss
gdsu
gdsw
gdt
gdtc
gdth
gdthc
gdtp
gdts
gdts1
gdu
gdw
gdw-
gdwc
gdws
geq
ger
get
gf
gf1
gfa
gfb
gfc
gfd
gfd1
gfd2
gfd3
gfe
gfer
gfes
gff
gfh
gfiles
gfiles
gfm
gfm1
gfn
gfnp
gfnr
gfns
gfo
gfor
gfp
gfpr
gfr
gfro
gfru
gfs
gft
gfta
gftd
gfu
gfua
gfue
gfun
gfune
gfur
gg
gga
ggaa
ggaal
ggad
ggadh
ggal
ggala
ggcd
ggd
ggg
gggc
gggid
gghu
ggi
ggid
ggidg
ggl
ggn
ggp
ggpi
ggpl
ggpn
ggpq
ggr
ggr10
ggra
ggrac
ggracd
ggracl
ggracle
ggrad
ggrd
ggrdh
ggrdn
ggre
ggrec
ggrh
ggrhu
ggrl
ggrn
ggru
ggsid
ggt
ggu
ggue
ggun
gh_job
gh_job_id
gh_job_ids
gh_job_url
gh_last_run_id
gh_last_workflow_run
gh_open_job
gh_open_last
gh_run_and_job
gh_run_list_in_progress
gh_run_open
gh_run_view_jobs
gh_run_view_url
gh_workflow_run
gh_workflow_run_current_branch
gha
ghaj
ghb
ghbi
ghbis
ghblr
ghblrs
ghbs
ghc
ghds
ghdss
ghf
ghh
ghj
ghji
ghjis
ghju
ghlr
ghlw
ghlwr
ghm
ghnc
gho
ghoa
ghob
ghoj
ghol
ghou
ghow
ghr
ghraj
ghrh
ghrl
ghrlh
ghrn
ghro
ghrp
ghrv
ghrvh
ghrvj
ghrvjs
ghrvl
ghrvlj
ghrvu
ghrvw
ghsdb
ghsh
ghw
ghwip
ghwl
ghwr
ghwrc
gib
gic
gicc
gid
gidc
gig
gir
gis
gism
gisr
gist-dir
git-add-and-cherry-pick-continue
git-add-and-commit-msg
git-add-global-file
git-add-global-ignore
git-add-mirror-remote
git-add-rebase-continue
git-add-rebase-continue-no-edit
git-all-commits
git-all-hashes
git-amend-force-push
git-bak
git-bisect-commits-ahead-good
git-bisect-commits-behind-bad
git-bisect-earliest-bad
git-bisect-latest-good
git-bisect-reverse-run
git-bisect-start-run
git-blames
git-blob-sha
git-branch-exists
git-branch-point
git-branch-reset
git-branch-reset-upstream
git-branch-reset-upstream-checkout
git-branch-upstream
git-branches
git-branches.py
git-cd-to-root
git-check-s3-buckets
git-checkout-and-rebase
git-checkout-previous-branch
git-cherry-pick-from-file
git-cherry-pick-head
git-cherry-pick-preserve-commit-date
git-cherry-pick-show-head
git-clean-branches
git-clone-and-cd
git-clone-single-branch
git-command-exists
git-commit-and-tag.sh
git-commit-basename
git-commit-basenames
git-commit-body
git-commit-multiple-parents
git-commit-push
git-commit-push-parents
git-commit-rebase-head
git-commit-tree-reset
git-conflict-lines
git-conflicting
git-conflicting-checkout
git-conflicting-checkout-ours-and-continue
git-conflicting-checkout-theirs-and-continue
git-convert-links-to-aliases
git-copy-author
git-copy-diffs
git-copy-diffs-rsync
git-count
git-count-commits
git-default-remote
git-delete-merged-branches
git-diff-branch-reflog
git-diff-filter
git-diff-gif.py
git-diff-json.py
git-diff-name-only-all
git-diff-no-context
git-diff-pipe
git-diff-stat-parent
git-diff-theirs
git-diff-theirs-conflicting
git-diff-then-maybe-add
git-diff-vs-parent
git-equal
git-fetch-x
git-filter-to-dir
git-find
git-find-broken-links
git-find-only-remote
git-find-prefix
git-find-suffix
git-fix-broken-links
git-fixup-author
git-full-hash
git-get-id
git-get-only-remote
git-get-tag
git-git-dir
git-graph
git-graph-all
git-hash
git-head-before-last-rebase
git-help-follow
git-is-branch
git-is-repo
git-is-submodule
git-is-tag
git-kill-lines
git-links
git-list-n
git-list-status
git-list-unstaged
git-load-github-prs
git-local-branch-shas
git-local-branches
git-log-1-format
git-log-format
git-log-hash
git-log-oneline
git-lookup-links
git-ls-hashes
git-ls-new-files
git-lsub
git-me-push
git-me-push-force
git-merge-base-parents
git-merge-base-plus
git-merge-base-tracked-branch
git-merge-head
git-mirror-remote
git-mount-branch
git-mv-aliases
git-my-clone
git-new-branch
git-octomerge
git-original-commit
git-original-head
git-parents.py
git-patch-branch-diff
git-pre-rebase-head-log
git-pre-rebase-head-log-pretty
git-push-head-to
git-push-head-upstream
git-push-parents
git-push-to-master
git-push-to-remote-branch
git-push-user-branch
git-push-x
git-rebase-branch
git-rebase-branches
git-rebase-dag.py
git-rebase-diff
git-rebase-head
git-rebase-head-message
git-rebase-head-submodule-log
git-rebase-inline
git-rebase-merge-base
git-rebase-onto
git-rebase-parent
git-rebase-preserve-commit-dates
git-rebase-sequence
git-rebase-stdin
git-rebase-undo
git-rebase-upstream-diff
git-recreate-file
git-relpath
git-remote-add.py
git-remote-branch-exists
git-remote-branches
git-remote-copy
git-remote-default-branch
git-remote-exists
git-remote-get-url
git-remote-path
git-remote-rename
git-remote-set-head
git-remote-set-head-auto
git-remote-set-url
git-remote-url-to-https
git-remotes
git-reorder-commits
git-reset-committer-date-rebase-head
git-reset-hard
git-restore-worktree
git-rev-list-first-parents
git-reverse-reset
git-revert-last-rebase
git-rewrite-author
git-rm-deleted
git-rm-untracked
git-safe-apply
git-safe-push-force
git-serve
git-set-author
git-set-author-date
git-set-committer-date
git-set-dates
git-set-id
git-set-parents
git-set-sha
git-show-apply
git-show-head
git-show-head-file
git-show-local-names
git-show-merge-base
git-show-merge-head
git-show-names
git-show-original-commit
git-show-original-head
git-show-rebase-head
git-show-remote-names
git-show-sha-file
git-show-short
git-size
git-sizes
git-squash
git-squash-head-onto
git-squash-range
git-squash-sequence
git-squashed-commit-message
git-ssh-command
git-stash-save
git-stash-view
git-status-x
git-sub
git-submodule-auto-commit
git-submodule-commits
git-submodule-count-commits
git-submodule-github-repo
git-submodule-log
git-submodule-rebase-continue.py
git-submodule-rebase-log.py
git-submodule-sha
git-submodule-shas
git-submodule-url
git-submodules
git-tags
git-throw.py
git-tracked-branch
git-unbak
git-undelete
git-unpack-and-apply-diffs
git-user
git-version-greater-than-or-equal-to
git-watchman-copy-diffs
git-watchman-copy-diffs-stop
git_dir_curry
git_set_sha
github
github-api-url
github-commit-api-urls
github-commit-web-urls
github-docs-snapshot
github-submodule-check-commits
github-web-url
github-workflows.py
github_maybe_api
github_open_actions
github_open_web_branch
github_parse_remote_and_branch
github_remote
github_remote_path
github_set_default_branch
github_url
gitlab_api
gitlab_maybe_api
gitlab_open_jobs
gitlab_parse_remote_and_branch
gitlab_protect_branch
gitlab_remote
gitlab_remote_path
gitlab_set_default_branch
gitlab_unprotect_branch
gkl
gl
gl1
gl1T
gl1f
gl1fT
gl1ft
gl1t
gla
gladr
glaf
glapi
glb
glbl
glbs
glc
glc1
glcc
glcs
glcu
gld
gldc
glds
gldu
glf
glf1
glg
glgf
glgf1
glgg
glggp
glgp
glgpg
glgs
glm
glmm
gln
gln1
gln2
gln20
gln3
gln4
gln5
gln6
gln7
gln8
gln9
glnf
glno
glns
glnw
glo
glob
globj
gloj
gloz
glp
glpb
glpbn
glpp
glpr
glr
glrh
glrn
glrp
glrpe
glrt
gls
glsc
glsdb
glsf
glso
glsr
glsrh
glsrt
glst
glsu
glt
glth
glthn
glthr
gltr
gltrn
glts
gltsh
glu
glub
glubn
glw
glws
glz
glzo
gm
gma
gmb
gmbo
gmbp
gmbt
gmc
gmf
gmff
gmh
gmm
gmmne
gmn
gmne
gmnef
gmnf
gmnm
gmnnf
gmr
gmsg
gmt
gmtb
gmtnb
gmu
gmun
gmune
gmv
gn
gnb
gnd
gndc
gndh
gnfm
gngp
gnx
goc
goh
gom
gp
gpb
gpbd
gpd
gpf
gpfn
gpfo
gpft
gpftn
gpfu
gph
gphf
gphfn
gphn
gpht
gphu
gphuf
gphufn
gphun
gpie
gpl
gpm
gpn
gpnf
gpno
gpnt
gpnu
gpo
gpon
gpot
gpp
gppa
gppam
gppm
gppr
gpps
gpr
gprhl
gprhlh
gprnts
gps
gpsu
gpt
gptf
gptn
gpto
gpts
gptu
gpu
gpub
gpubf
gpubn
gpun
gput
gpx
gr
gr.
gra
grah
grao
gras
grat
grau
grb
grba
grbb
grbc
grbcd
grbcda
grbd
grbe
grbh
grbhm
grbi
grbm
grbmb
grbo
grbor
grbori
grbot
grbp
grbr
grbrio
grbro
grbs
grbsi
grbsin
grbu
grbud
grc
grcd
grcdrbh
grcp
grd
grdb
gre
grgh
grgu
grh
grh1
grhh
grhl
grhlh
grhm
grhp
grhsl
gri
grim
grio
grir
grit
grix
grl
grla
grlc
grlfp
grlh
grlp
grlp1
grlrb
grlt
grm
grmc
grmcf
grmf
grmlo
grmlso
grmp
grmpe
grmr
grmrc
grmu
grmut
grmv
grne
grneh
grnh
gro
groc
grocn
grp
grph
grq
grr
grri
grrio
grrm
grro
grrs
grs
grs.
grsf
grsh
grsha
grsi
grsin
grsp
grss
grsu
grt
grtc
grtch
grud
gruh
grv
grvl
grvne
grvneh
grvp
grvph
grvt
grvth
grw
grwa
grx
gs
gsa
gsac
gsaca
gsad
gsau
gsaut
gsb
gsbj
gsc
gscd
gsd
gsdbm
gsdc
gsdh
gsds
gsf
gsfh
gsfv
gsg
gsgid
gsh
gsha
gshadr
gshc
gshch
gshd
gshf
gshfp
gshh
gshhf
gshl
gshm
gshmb
gshmh
gshmr
gshms
gshno
gshns
gsho
gshoc
gshoh
gshon
gshp
gshp2
gshp3
gshrh
gshrm
gshs
gshsl
gshss
gshw
gsid
gsidg
gsj
gsk
gsl
gslg
gsln
gsm
gsma
gsmac
gsmc
gsmcc
gsmd
gsmf
gsmg
gsmh
gsmi
gsmid
gsmir
gsml
gsmlf
gsmlg
gsmlp
gsmn
gsmp
gsmr
gsmrs
gsms
gsmsh
gsmsha
gsmshs
gsmst
gsmt
gsmu
gsmuf
gsmuq
gsmur
gsmurf
gsmurq
gsmurr
gsmus
gsn
gsnl
gsnr
gsp
gsp1
gsp2
gsp3
gsp4
gsp5
gspf
gspfo
gspfu
gsps
gsqsq
gsr
gsrc
gsrl
gsrlv
gsrn
gsrs
gsru
gsrv
gss
gssf
gssh
gssk
gssp
gsst
gst
gstd
gsth
gstp
gsts
gsu
gsuf
gsuq
gsur
gsurq
gsus
gsw
gsw0
gsw1
gsw2
gsw3
gsx
gsz
gszh
gszs
gt
gta
gtb
gtc
gtd
gtf
gtfi
gtg
gth
gti
gtl
gtn
gtp
gtr
gtr0
gtrh
gtrp
gtrr
gts
gtsz
gtw
gtwh
gtwhn
gtwp
gtwp2
gtwp3
gub
gud
gue
gun
gune
gup
gur
gus
gusi
gusr
guu
gwd
gx
gxb
gxc
gxca
gxcam
gxcap
gxcapm
gxd
gxg
gxh
gxl
gxr
gxs
gxt
hash-files.py
hb
hds
hdss
hpr
hprq
init-mirror-remote
issues
lff
lfl
lfp
lfs
ls-remote
mk-git
p
parse-github-url
pgr
pop-arg
pop_commit_from_file
rb
rbo
repos.py
root_dir
root_setup
1033 completions present before and after installing git-helpers
1231 completions added by installing git-helpers (0 removed, 2264 total)
```
</details>

### Most-used aliases <a id="aliases"></a>
Here's a snapshot of my most-used Git aliases::
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

[`git-reset-committer-date-rebase-head`]: rebase/git-reset-committer-date-rebase-head
[`git-throw`]: rebase/git-throw.py

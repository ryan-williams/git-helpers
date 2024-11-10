# git-helpers
[1,261](#count-completions) Git aliases and scripts.

<!-- toc -->
- [Stats](#stats)
    - [Count aliases](#count-completions)
    - [Most-used aliases](#aliases)
- [Setup](#setup)
- [Commands](#commands)
    - [Inspect commit graph](#graphs)
        - [`ggr` (`git-graph`)](#ggr)
        - [`gg` (`git-graph-all`)](#gg)
    - [Summarize local/remote branches](#branches)
        - [`gb` (`git branches`)](#gb)
        - [`gbr` (`git-remote-branches`)](#gbr)
    - [Inspect commits being rebased/cherry-picked](#gshrh)
        - [`grbh` (`git-rebase-head`), `gcph` (`git-cherry-pick-head`)](#grbh)
        - [`gshrh` (`git-show-rebase-head`), `gshch` (`git-show-cherry-pick-head`)](#gshrh)
    - [Rebase](#rebase)
        - [`gtw` (`git-throw`)](#gtw)
        - [`groc` (`git-reorder-commits`)](#groc)
        - [`grbcd` (`git-rebase-preserve-commit-dates`)](#grbcd)
        - [`gec` (`git-edit-commit`)](#gec)
        - [Other](#rebase-other)
    - [Diff helpers, GIFs, JSON](#diff)
        - [`gdg` (`git-diff-gif.py`)](#gdg)
        - [`gdj` (`git-diff-json.py`)](#gdj)
    - [Update commit parents](#parents)
<!-- /toc -->

## Stats <a id="stats"></a>

### Count aliases <a id="count-completions"></a>
Most aliases in this repo begin with `g` (for Git). [count-completions.sh](scripts/count-completions.sh) counts them:
<!-- `bmdf -- scripts/count-completions.sh -c` -->
```bash
scripts/count-completions.sh -c
# 1306 completions added by installing git-helpers
# By length:
# - 2 chars: 15
# - 3 chars: 230
# - 4 chars: 488
```

A goal of this repo is to help me always be within a couple keystrokes of most common Git commands.

Here's a full list of the aliases and scripts provided by `source`ing [`.git-rc`](.git-rc):

<!-- `bmdfff -- scripts/count-completions.sh -v` -->
<details><summary><code>scripts/count-completions.sh -v</code></summary>

```
1306 new completions:
g
p
g1
ga
gb
gc
gd
gf
gg
gl
gm
gn
gp
gr
gs
gt
gx
hb
rb
g1f
ga.
gab
gac
gad
gae
gaf
gah
gai
gan
gap
gar
gau
gbD
gbb
gbc
gbd
gbe
gbf
gbh
gbk
gbp
gbr
gbs
gbu
gby
gca
gcb
gcd
gce
gcf
gcg
gch
gci
gcl
gcm
gcn
gco
gcp
gct
gd-
gda
gdb
gdc
gdd
gdf
gdg
gdh
gdj
gdl
gdn
gdp
gdq
gdr
gds
gdt
gdu
gdw
gec
geq
ger
get
gf1
gfa
gfb
gfc
gfd
gfe
gff
gfh
gfm
gfn
gfo
gfp
gfr
gfs
gft
gfu
gga
ggd
ggg
ggi
ggl
ggn
ggp
ggr
ggt
ggu
gha
ghb
ghc
ghf
ghh
ghj
ghm
gho
ghr
ghu
ghw
ghx
gib
gic
gid
gig
gir
gis
gkl
gl1
gla
glb
glc
gld
glf
glg
glh
glm
gln
glo
glp
glr
gls
glt
glu
glw
glz
gma
gmb
gmc
gmf
gmh
gmm
gmn
gmr
gmt
gmu
gmv
gnb
gnd
gnx
goc
goh
gom
gpb
gpd
gpf
gph
gpl
gpm
gpn
gpo
gpp
gpr
gps
gpt
gpu
gpx
gr.
gra
grb
grc
grd
gre
grh
gri
grl
grm
grn
gro
grp
grq
grr
grs
grt
grv
grw
grx
gsa
gsb
gsc
gsd
gsf
gsg
gsh
gsj
gsk
gsl
gsm
gsn
gsp
gsr
gss
gst
gsu
gsw
gsx
gsz
gta
gtb
gtc
gtd
gtf
gtg
gth
gti
gtl
gtn
gtp
gtr
gts
gtw
gub
gud
gue
gun
gup
gur
gus
guu
gwd
gwh
gwt
gxb
gxc
gxd
gxg
gxh
gxl
gxr
gxs
gxt
hds
hpr
lff
lfl
lfp
lfs
pgr
rbo
gabd
gabt
gabu
gace
gacm
gaeg
gael
gafp
gage
gagi
gamr
gap.
gapf
gaps
gapu
garc
garn
gau.
gauf
gaup
gaus
gaut
gbdf
gbeb
gbfc
gbhi
gbhs
gblg
gbls
gbmv
gbpa
gbrg
gbrh
gbrm
gbrr
gbrs
gbru
gbsb
gbsg
gbsh
gbsl
gbsn
gbsr
gbss
gbsx
gcaa
gcae
gcaf
gcam
gcan
gcap
gcbh
gcbn
gccd
gcfa
gcfd
gcfi
gcfl
gcfp
gcfs
gcft
gcfu
gcga
gcgd
gcgi
gcgl
gcgs
gcgu
gchf
gciv
gclb
gcln
gcmb
gcmf
gcmp
gcmt
gcnb
gcne
gcnf
gcnm
gco-
gcob
gcof
gcoh
gcom
gcon
gcoo
gcop
gcor
gcot
gcp1
gcp2
gcpa
gcpc
gcpd
gcph
gcpm
gcpn
gcpp
gcps
gcrb
gcrh
gcs3
gcsb
gcsp
gctg
gctp
gctr
gdas
gdbm
gdbr
gdbt
gdbu
gdc-
gdcp
gdcs
gdcw
gddf
gdfm
gdfr
gdft
gdh1
gdh2
gdir
gdma
gdmb
gdno
gdns
gdp1
gdp2
gdph
gdps
gdrb
gds1
gdsc
gdsd
gdsh
gdsl
gdsp
gdss
gdsu
gdsw
gdt1
gdtc
gdth
gdtl
gdtp
gdts
gdw-
gdwc
gdws
gecn
gecp
gecr
gecx
gfd1
gfd2
gfd3
gfer
gfes
gfm1
gfnp
gfnr
gfns
gfor
gfpr
gfro
gfru
gfta
gftd
gfua
gfue
gfun
gfur
ggaa
ggad
ggal
ggcd
ggdb
gggc
gggi
gghu
ggid
ggpi
ggpl
ggpn
ggpq
ggra
ggrd
ggre
ggrh
ggrl
ggrn
ggru
ggue
ggun
ghaj
ghax
ghbi
ghbs
ghds
ghji
ghju
ghlr
ghlw
ghnc
ghoa
ghob
ghoc
ghoj
ghol
ghor
ghow
ghrh
ghrl
ghrn
ghro
ghrp
ghrv
ghsh
ghub
ghwl
ghwr
gicc
gidc
gism
gisr
gl1T
gl1f
gl1t
glaf
glbl
glbs
glc1
glcc
glcs
glcu
gldc
glds
gldu
glf1
glgf
glgg
glgp
glgs
glmm
gln1
gln2
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
glob
gloj
gloz
glpb
glpp
glpr
glrh
glrn
glrp
glrt
glsc
glsf
glso
glsr
glst
glsu
glth
gltn
gltr
glts
glub
glws
glzo
gmbo
gmbp
gmbt
gmff
gmne
gmnf
gmnm
gmsg
gmtb
gmun
gnbl
gnbr
gndc
gndh
gnfm
gngp
gnlh
gnsh
gpbd
gpfn
gpfo
gpft
gpfu
gphf
gphn
gpht
gphu
gpie
gpnf
gpno
gpnt
gpnu
gpon
gpot
gppa
gppm
gppr
gpps
gpsu
gptf
gptn
gpto
gpts
gptu
gpub
gpun
gput
grah
grao
gras
grat
grau
grba
grbb
grbc
grbd
grbe
grbh
grbi
grbm
grbo
grbp
grbr
grbs
grbu
grcd
grcp
grdb
grel
grgh
grgu
grh1
grhh
grhl
grhm
grhp
grim
grio
grir
grit
grix
grla
grlc
grlh
grlp
grlt
grmc
grmf
grmp
grmr
grmu
grmv
grne
grnh
groc
grph
grri
grrm
grro
grrs
grs.
grsf
grsh
grsi
grsp
grss
grsu
grtc
grud
gruh
grvl
grvn
grvp
grvt
grwa
grwc
grwt
gsac
gsad
gsaf
gsau
gsbj
gscd
gsdc
gsdh
gsdr
gsds
gsfh
gsfv
gsha
gshc
gshd
gshf
gshh
gshl
gshm
gsho
gshp
gshs
gshw
gsid
gsig
gslg
gsln
gsma
gsmc
gsmd
gsmf
gsmg
gsmh
gsmi
gsml
gsmn
gsmp
gsmr
gsms
gsmt
gsmu
gsnl
gsnr
gsp1
gsp2
gsp3
gsp4
gsp5
gspf
gsps
gsrc
gsrl
gsrn
gsrs
gsru
gsrv
gssf
gssh
gssk
gssp
gsst
gstd
gsth
gstp
gsts
gsuf
gsuq
gsur
gsus
gsw0
gsw1
gsw2
gsw3
gswc
gswr
gszh
gszs
gtfi
gtr0
gtrh
gtrp
gtrr
gtsz
gtwh
gtwp
gune
gusi
gusr
gxca
hdss
hprq
gaafp
gaapf
gacpc
gadi1
gapfu
gapu.
garcn
gaup.
gbcag
gbcbb
gbhis
gbpar
gbruc
gbssr
gcaam
gcaan
gcaap
gcaem
gcamf
gcamt
gcane
gcapm
gcarb
gcbns
gcdi1
gcfda
gcfef
gcfia
gcfig
gcfis
gcfpd
gcfua
gcgda
gcgdb
gcgef
gcgia
gcgif
gcgig
gcgis
gcgpd
gcgua
gcmab
gcmba
gcmfa
gcmtf
gcmtr
gcoco
gcoct
gcorb
gcorf
gcpam
gcpau
gcpdc
gcpdu
gcppa
gcppm
gcpsh
gcrbh
gctgs
gdcno
gdcss
gdcw-
gdgif
gdmbr
gdnoa
gdnoc
gdnom
gdsca
gdsph
gdthc
gdts1
gecnp
gecnx
gecrn
gecrp
gecxn
gfune
ggaal
ggadh
ggala
ggdbm
gggid
ggidg
ggr10
ggrac
ggrad
ggrdh
ggrdn
ggrec
ggrhu
ggsid
ghbis
ghblr
ghdss
ghjis
ghlwr
ghpbs
ghraj
ghrlh
ghrvh
ghrvj
ghrvl
ghrvu
ghrvw
ghsdb
ghubn
ghwip
ghwrc
gl1fT
gl1ft
gladr
glapi
glgf1
glggp
glgpg
gln20
globj
glpbn
glrpe
glsdb
glsrh
glsrt
glthn
glthr
gltrn
gltsh
glubn
gmmne
gmnef
gmnnf
gmtnb
gmune
gnshs
gpftn
gphfn
gphuf
gphun
gppam
gprhl
gpubf
gpubn
grbcd
grbhm
grbmb
grbor
grbot
grbro
grbsi
grbud
grhlh
grhsl
grlfp
grlp1
grlrb
grmcf
grmlo
grmpe
grmrc
grmut
grneh
grocn
grrio
grsha
grsin
grtch
grvne
grvph
grvth
grvtn
gsaca
gsaut
gsdbm
gsdru
gsgid
gshch
gshfp
gshhf
gshmb
gshmh
gshmr
gshms
gshno
gshns
gshoc
gshoh
gshon
gshp2
gshp3
gshrh
gshrm
gshsl
gshss
gshwc
gsidg
gsmac
gsmaf
gsmcc
gsmid
gsmir
gsmlf
gsmlg
gsmlp
gsmrs
gsmsh
gsmst
gsmuf
gsmuq
gsmur
gsmus
gspfo
gspfu
gsqsq
gsrlv
gsurq
gtwhn
gtwp2
gtwp3
gxcam
gxcap
gaapfu
gcaane
gcaapm
gcamtf
gcanea
gcfefs
gcfigs
gcgefs
gcgigs
gcgpdc
gcgpdu
gcmtrr
gcococ
gcoctc
gcppam
gcppcd
gecrpn
gfiles
gfiles
ggracd
ggracl
gh_job
ghblrs
ghrvjs
ghrvlj
github
gphufn
gprhlh
gprnts
grbcda
grbori
grbrio
grbsin
grmlso
grvneh
gshadr
gshwch
gsmsha
gsmshs
gsmurf
gsmurq
gsmurr
gxcapm
issues
mk-git
ggracle
git-bak
git-sub
grcdrbh
pop-arg
gist-dir
git-find
git-hash
git-lsub
git-size
git-tags
git-user
repos.py
root_dir
gh_job_id
git-count
git-equal
git-graph
git-links
git-serve
git-sizes
git-unbak
ls-remote
gh_job_ids
gh_job_url
git-blames
git-get-id
git-is-tag
git-list-n
git-push-x
git-set-id
git-squash
github_url
gitlab_api
root_setup
gh_open_job
gh_run_open
git-fetch-x
git-get-tag
git-git-dir
git-is-repo
git-me-push
git-relpath
git-remotes
git-set-sha
git_set_sha
clone_org.py
gh_open_last
git-blob-sha
git-branches
git-log-hash
git-my-clone
git-status-x
git-throw.py
git-undelete
git-diff-pipe
git-full-hash
git-graph-all
git-is-branch
git-ls-hashes
git-octomerge
git-set-dates
git-show-head
git_dir_curry
github_remote
gitlab_remote
hash-files.py
gh_last_run_id
gh_run_and_job
git-all-hashes
git-cd-to-root
git-copy-diffs
git-kill-lines
git-log-format
git-merge-head
git-mv-aliases
git-new-branch
git-parents.py
git-reset-hard
git-rm-deleted
git-safe-apply
git-set-author
git-show-apply
git-show-names
git-show-short
git-stash-save
git-stash-view
git-submodules
github-api-url
github-web-url
gh_run_view_url
gh_workflow_run
git-all-commits
git-branches.py
git-commit-body
git-commit-push
git-conflicting
git-copy-author
git-diff-filter
git-diff-gif.py
git-diff-theirs
git-edit-commit
git-filter-repo
git-find-prefix
git-find-suffix
git-help-follow
git-list-status
git-log-oneline
git-rebase-diff
git-rebase-head
git-rebase-onto
git-rebase-undo
git-remote-copy
git-remote-path
git-set-parents
git-ssh-command
gh_run_view_jobs
git-branch-point
git-branch-reset
git-clone-and-cd
git-diff-json.py
git-fixup-author
git-is-submodule
git-log-1-format
git-lookup-links
git-ls-new-files
git-mount-branch
git-push-head-to
git-push-parents
git-rebase-stdin
git-rm-untracked
git-squash-range
github_maybe_api
gitlab_maybe_api
gitlab_open_jobs
parse-github-url
git-branch-exists
git-count-commits
git-filter-to-dir
git-list-unstaged
git-me-push-force
git-mirror-remote
git-original-head
git-rebase-branch
git-rebase-dag.py
git-rebase-inline
git-rebase-parent
git-recreate-file
git-remote-add.py
git-remote-exists
git-remote-rename
git-reverse-reset
git-show-sha-file
git-submodule-log
git-submodule-sha
git-submodule-url
git-clean-branches
git-command-exists
git-conflict-lines
git-default-remote
git-diff-vs-parent
git-local-branches
git-push-to-master
git-remote-get-url
git-remote-set-url
git-rewrite-author
git-show-head-file
git-submodule-shas
git-tracked-branch
git_filter_repo.py
github_remote_path
gitlab_remote_path
init-mirror-remote
git-add-global-file
git-branch-upstream
git-commit-basename
git-diff-no-context
git-get-only-remote
git-load-github-prs
git-merge-base-plus
git-original-commit
git-rebase-branches
git-rebase-sequence
git-remote-branches
git-remote-set-head
git-reorder-commits
git-safe-push-force
git-set-author-date
git-show-merge-base
git-show-merge-head
git-squash-sequence
github-workflows.py
github_open_actions
github_open_web_ref
gh_last_workflow_run
git-amend-force-push
git-bisect-start-run
git-check-s3-buckets
git-cherry-pick-head
git-commit-basenames
git-copy-diffs-rsync
git-diff-stat-parent
git-find-only-remote
git-fix-broken-links
git-push-user-branch
git-restore-worktree
git-show-local-names
git-show-rebase-head
git-squash-head-onto
github-docs-snapshot
pop_commit_from_file
git-add-core-excludes
git-add-global-ignore
git-add-mirror-remote
git-commit-and-tag.sh
git-commit-tree-reset
git-find-broken-links
git-local-branch-shas
git-patch-branch-diff
git-rebase-merge-base
git-show-remote-names
git-submodule-commits
gitlab_protect_branch
git-add-and-commit-msg
git-bisect-latest-good
git-bisect-reverse-run
git-commit-rebase-head
git-diff-branch-reflog
git-diff-name-only-all
git-merge-base-parents
git-push-head-upstream
git-revert-last-rebase
git-set-committer-date
git-show-original-head
github-commit-api-urls
github-commit-web-urls
github_open_web_branch
github_open_web_commit
gh_run_list_in_progress
git-add-rebase-continue
git-bisect-earliest-bad
git-checkout-and-rebase
git-clone-single-branch
git-commit-push-parents
git-diff-then-maybe-add
git-pre-rebase-head-log
git-rebase-head-message
git-remote-url-to-https
github_unprotect_branch
gitlab_unprotect_branch
git-conflicting-checkout
git-rebase-upstream-diff
git-remote-branch-exists
git-remote-set-head-auto
git-show-original-commit
git-branch-reset-upstream
git-cherry-pick-from-file
git-cherry-pick-show-head
git-push-to-remote-branch
git-remote-default-branch
git-submodule-auto-commit
git-submodule-github-repo
github_protected_branches
github_set_default_branch
gitlab_set_default_branch
git-delete-merged-branches
git-rev-list-first-parents
git-unpack-and-apply-diffs
git-commit-multiple-parents
git-diff-theirs-conflicting
git-head-before-last-rebase
git-squashed-commit-message
git-submodule-count-commits
git-submodule-rebase-log.py
git-checkout-previous-branch
git-convert-links-to-aliases
git-bisect-commits-ahead-good
git-bisect-commits-behind-bad
git-merge-base-tracked-branch
git-rebase-head-submodule-log
gh_workflow_run_current_branch
git-pre-rebase-head-log-pretty
github-submodule-check-commits
github_parse_remote_and_branch
gitlab_parse_remote_and_branch
git-add-rebase-continue-no-edit
git-add-and-cherry-pick-continue
git-rebase-preserve-commit-dates
git-submodule-rebase-continue.py
git-branch-reset-upstream-checkout
git-cherry-pick-preserve-commit-date
git-reset-committer-date-rebase-head
git-version-greater-than-or-equal-to
git-conflicting-checkout-ours-and-continue
git-conflicting-checkout-theirs-and-continue
1255 completions present before and after installing git-helpers
1306 completions added by installing git-helpers (0 removed, 2561 total)
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
`ggr` ([`git-graph`]) and `gg` ([`git-graph-all`]) are my preferred ways to visualize Git branches and history.

#### `ggr` ([`git-graph`]) <a id="ggr"></a>

Example output from this repo:

![](img/gg-git-helpers.png)

The first line shows that local branch `main` is checked out (`HEAD -> main`), and up to date with remote branches `gh/main` and `gl/main` (GitHub and GitLab, resp., but that's just a convention I use).

#### `gg` ([`git-graph-all`]) <a id="gg"></a>
Same as [`ggr`](#ggr), but includes all branches (not just the current one).

e.g., [runsascoded/.rc] shows several parallel branch lineages I maintain:

![](img/gg-rc.png)

I develop on `gh-all`, and cherry-pick commits over to `gh-server`, `gl-all`, and `gl-server`.

[git/git] shows wide merge lineages

![](img/gg-git.png)

### Summarize local/remote branches <a id="branches"></a>

#### `gb` ([`git branches`]) <a id="gb"></a>

Improved version of `git branch -vv`:
- Branches output in reverse-chron order of last modification (instead of alphabetically)
- Nice colors for each field
- Concise "commits ahead/behind" counts
- Abbreviated "time since last commit"

[TileDB-SOMA] example:

![gb](img/gb-tdbs.png)

#### `gbr` ([`git-remote-branches`]) <a id="gbr"></a>

Similar to [`gb`](#gb), but summarizes remotes' branches.

### Inspect commits being rebased/cherry-picked <a id="gshrh"></a>

#### `grbh` ([`git-rebase-head`]), `gcph` ([`git-cherry-pick-head`]) <a id="grbh"></a>
Print the SHA of the commit currently being rebased or cherry-picked.

#### `gshrh` ([`git-show-rebase-head`]), `gshch` ([`git-show-cherry-pick-head`]) <a id="gshrh"></a>
Pass the above SHAs to `git show`.

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

#### `groc` ([`git-reorder-commits`]) <a id="groc"></a>
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
In this case, calls to [`git reset-committer-date-rebase-head`] are inserted after each `pick`ed commit.

The `rebase -x` flag is also directly available; this does the same as the above:

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

#### `grbcd` ([`git-rebase-preserve-commit-dates`]) <a id="grbcd"></a>
Rebase, but inject `-x git rcd` ([`git reset-committer-date-rebase-head`]) after each commit, so that the committer-time is preserved.

#### `gec` ([`git-edit-commit`]) <a id="gec"></a>
Run a rebase to `edit` or `reword` a specific commit:

```bash
# Open the 3th commit back from HEAD, in rebase "edit" mode.
# A subsequent `rebase --continue` will rebase the remaining 3 commits on top of it.
git edit-commit HEAD~3

# "Dry run" of the above:
git edit-commit -n HEAD~3
# Would run git rebase -i d6aae97^:
# edit d6aae97 rm orphaned(?) `commit-filename{,s}` aliases
# pick ed9447b `cmba="commit-body -a"`, `cnb="commit-body --amend"`
# pick df33af4 `git-diff-json.py` fixes
# pick 3c166c3 `dtl`/`details`: commit details

# Change the parent commit's message, rebase HEAD on top of it (noninteractive)
git edit-commit -r "new message" HEAD^

# Same as above, but preserve the "committer dates" of `HEAD^` and `HEAD` (`g rcd` = `git reset-committer-date-rebase-head`)
git edit-commit -r "new message" -x "g rcd" HEAD^

# As a demonstration, this is effectively a no-op (same HEAD SHA before and after).
# `gby = git body = git log -1 --format=%B`, so this rewrites the parent commit with the same
# message, and preserves its committer date.
git edit-commit -r "`gby HEAD^`" -x "g rcd" HEAD^
```

#### Other <a id="rebase-other"></a>
- `rb <N>`: interactive rebase over the last `N` commits.
- `grd` ([`git-rebase-diff`]): compute most recent pre-rebase SHA (`ghblr` / [`git-head-before-last-rebase`]), diff that vs. current worktree.
  - Useful to ensure a rebase didn't change the final work-tree, e.g. when combining or rearranging commits.

### Diff helpers, GIFs, JSON <a id="diff"></a>
- `gdc` (`git diff --cached`): show staged changes only
- `gds` (`git diff --stat`): show file/line add/remove stats
- `gdw` (`git diff -w`): diff, ignoring whitespace changes

Most combos of the above also exist, e.g. `gdcs`, `gdsw`, etc.

#### `gdg` ([`git-diff-gif.py`]) <a id="gdg"></a>
Create a GIF of an image at two commits, open in browser.

#### `gdj` ([`git-diff-json.py`]) <a id="gdj"></a>
Pretty-print JSON files, before diffing them.

### Update commit parents <a id="parents"></a>
Create a commit with a given tree and parents:
- `gcmp` ([`git-commit-multiple-parents`]): takes an optional commit message (`-m`) and commit (`-b`) whose tree to use
- `gsp` ([`git-set-parents`]) uses the current `HEAD`s message and tree

### Author/Committer/User metadata
- `gsau` ([`git-set-author`]): update `HEAD` author, either from Git configs, an existing commit, or literal name/email arguments.
- `gsad` ([`git-set-author-date`]): update `HEAD` author date; match another commit's, or `HEAD`'s committer date.
- `gscd` ([`git-set-committer-date`]): update `HEAD` committer date; match another commit's, or `HEAD`'s author date.
- `gsid` ([`git-set-id`]), `ggsid` (`git-set-id -g`): set `user.{name,email}` configs.


[runsascoded/.rc]: https://github.com/runsascoded/.rc
[git/git]: https://github.com/git/git
[hammerlab/guacamole]: https://github.com/hammerlab/guacamole
[TileDB-SOMA]: https://github.com/TileDB-Inc/TileDB-SOMA

[`git reset-committer-date-rebase-head`]: rebase/git-reset-committer-date-rebase-head
[`git-throw`]: rebase/git-throw.py
[`git-rebase-preserve-commit-dates`]: rebase/git-rebase-preserve-commit-dates
[`git-reorder-commits`]: rebase/git-reorder-commits
[`git-graph`]: graph/git-graph
[`git-graph-all`]: graph/git-graph-all
[`git branches`]: branch/git-branches
[`git-commit-multiple-parents`]: commit/git-commit-multiple-parents
[`git-set-author`]: commit/git-set-author
[`git-set-author-date`]: commit/git-set-author-date
[`git-set-committer-date`]: commit/git-set-committer-date
[`git-set-id`]: config/git-set-id
[`git-set-parents`]: commit/git-set-parents
[`git-edit-commit`]: rebase/git-edit-commit
[`git-rebase-diff`]: rebase/git-rebase-diff
[`git-head-before-last-rebase`]: rebase/git-head-before-last-rebase
[`git-diff-gif.py`]: diff/git-diff-gif.py
[`git-diff-json.py`]: diff/git-diff-json.py
[`git-rebase-head`]: rebase/git-rebase-head
[`git-cherry-pick-head`]: cherry-pick/git-cherry-pick-head
[`git-show-rebase-head`]: rebase/git-show-rebase-head
[`git-show-cherry-pick-head`]: cherry-pick/git-cherry-pick-show-head

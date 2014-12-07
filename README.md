[![Build Status](https://travis-ci.org/ryan-williams/git-helpers.svg)](https://travis-ci.org/ryan-williams/git-helpers)

git-helpers
===========

A few helpers for augmenting and prettifying existing git functionality.

These were written alongside other bash and python helpers that I may not have ported; let me know if you see anything missing or broken.

### Setup
* `source .git-rc` from your `.bashrc`. This will give you lots of helpful aliases!
    * You might want to make sure it's not clobbering ones you already have/use.
    * It will also put several relevant directories from this repo on your `$PATH`

### "git branches" (`git b`) ###

I have this aliased to `gb` and it is one of my most commonly typed commands. It is basically a prettier and more useful version of `git branch -vv`.

Before:

![git branch -vv](http://f.cl.ly/items/3G3E123m293R2w3q0b36/Screen%20Shot%202014-09-08%20at%2010.29.21%20AM.png)

After:

![gb](http://f.cl.ly/items/1w310Q0S3n0a3f1K1u29/Screen%20Shot%202014-09-08%20at%2010.29.46%20AM.png)

Things to note:
* It sorts branches in reverse-chron order of last modification, instead of alphabetically
* It has nice colors for each field
* It has quick, at-a-glance "# commits ahead" and "# commits behind"
* It shows abbreviated "time since last commit"


#### Related: "git remote-branches" (`git br`) ####

A cousin of `git b` is `git br`, which basically does the same thing for remote branches / `git remote -v`:

Before:

![git branch -r -vv](http://f.cl.ly/items/0T2W0t3g0n2S3N240l33/Screen%20Shot%202014-09-08%20at%2010.40.02%20AM.png)

After:

![git remote-branches](http://f.cl.ly/items/2z1l0M1R3m2I2C3k1l2e/Screen%20Shot%202014-09-08%20at%2010.40.23%20AM.png)


### Push Repository State to Remote: `git copy-diffs` (`git cd`) ###

I have this aliased to `gcd` and for some workflows use it very frequently.

`git-cd` pushes the state of your local repository to a "mirror" remote, preserving:
* existing branches / `HEAD` pointer
* staged changes
* unstaged changes

I've been shocked to not find support for this in `git` itself, or in any other tools people have written that solve versions of this problem. Common approaches (none of which do exactly what I want, or have undesired side-effects) are:
* commit all uncommitted changes, then push to remote.
    * optionally repeatedly amend the top commit and `push -f` that.
    * I want to preserve what is committed vs. not.
* use `rsync`
    * You really want to only push git-tracked files, not the entire `git` directory (including e.g. `.git/`).
    * Seems pretty non-trivial to pipe e.g. the output of `git ls-files` to `rsync` in a way that `rsync` can digest.
        * `rsync`'s `--include*` options need entries for mid-level directories, which `git ls-files` does not print for you.
    * Fundamentally, feels like we should be using the fact that `git` is already a tracker of what you've changed / what files are under version-control.

#### Usage

Before using `git cd`, you'll want to set up a "mirrored" remote repository to push to. Luckily, `git add-mirror-remote` is here to help you!

    $ git add-mirror-remote dev-box ryan@dev-box:path/to/repo

Then you can say:

    $ git copy-diffs dev-box

And all of your state will be pushed to your remote, clobbering whatever was there previously.

As a shortcut, you can set environment variable `$MIRROR_REMOTES` to a comma-seperated list of remote names for `git copy-diffs` to look for by default:

    $ export MIRROR_REMOTES=dev-box
    $ git copy-diffs

Finally, you may want to preserve certain git-untracked files in the remote repo; you can do this by setting the environment variable `$GIT_COPY_DIFFS_PRESERVE_UNTRACKED`.
Alternatively, you can put multiple patterns in a file and set the environment variable `$GIT_COPY_DIFFS_PRESERVE_UNTRACKED_FILE` to the path to that file. Either way, `git-copy-diffs`
will ship those patterns to the remote and leave those files alone.

### "g" wrapper for `git`

Self-explanatory! Who has time for that extra "it" all the time?

### "rb": interactive rebase

Usage:

    $ rb 10  # interactive rebase over the last 10 commits

Short for `git rebase -i HEAD~<n>..HEAD`, or interactive rebase over the last `n` commits.

### git safe-push-force (`git spf`)

Typing `git push -f` is terrifying (rightly so)! Even when you *know* you're just force-pushing a feature branch that is ok to clobber, you are mere characters away from disaster.

`git safe-push` (a.k.a. `g spf`) will:
* try a non-force push
* if that fails, it will:
    * dry-run a force-push so that you can see what you're about to do,
    * tell you how many commits [what you're about to push] and [what you're about to overwrite] are away from one another,
    * ask whether you want to proceed,
    * if "Y" (default), then it will execute the `push -f` you've requested.

Sample output:
```
    # Inspect local branches; I have rearranged the order of the top two commits on `master`, and want to force-push that.
    $ gb
    * master 62a4888 origin/master +2 -2 18s 2014-09-08 15:03:57 some maven compile helpers
      test   4915c28 origin/master    -5  5d 2014-09-03 20:06:25 add `git-local-branches` helper

    # safe-push to the rescue!
    $ g spf master
    Safe-pushing master to origin/master (origin master)
    Non-fast-forward push? Dry-running -f: git push -f -n 'origin' 'master'
    To git@github.com:ryan-williams/bootstrap.git
     + 62f6ac4...62a4888 master -> master (forced update)

    	Merge base: 8479c0e
    	master: +2 commits
    	origin/master: +2 commits

    Continue? [Y/n]:
    git push -f 'origin' 'master'
    Counting objects: 10, done.
    Delta compression using up to 4 threads.
    Compressing objects: 100% (4/4), done.
    Writing objects: 100% (4/4), 521 bytes | 0 bytes/s, done.
    Total 4 (delta 2), reused 0 (delta 0)
    To git@github.com:ryan-williams/bootstrap.git
     + 62f6ac4...62a4888 master -> master (forced update)
```

It also has some handy refspec parsing, so all of the following are equivalent:
    $ g spf feature-branch ryan-feature-branch
    $ g spf origin feature-branch ryan-feature-branch
    $ g spf origin feature-branch:ryan-feature-branch
    $ g spf feature-branch:ryan-feature-branch

(if there is name ambiguity between a remote and a local branch, it will error out).

### "g lg" (pretty `git log -n`)

I have this aliased to `gln`.

Before:

![git log -n 4](http://f.cl.ly/items/1l3e020Q0r2c3u33253X/Screen%20Shot%202014-09-08%20at%2011.15.40%20AM.png)

After:

![gln 4](http://f.cl.ly/items/0v3X241T1i2O2f070D0h/Screen%20Shot%202014-09-08%20at%2011.15.24%20AM.png)

### Testing
`./run-tests` will run the bash and python tests in this repository, and is what Travis runs.

The python tests require some configuration to run locally:

```bash
virtualenv env
source env/bin/activate
pip -r requirements.dev.txt
nosetests
```

This is not necessary if you just want to use the scripts!




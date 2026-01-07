# Rebase Refspec Aliases

Aliases for comparing changes during and after rebases, especially useful with [git-didi].

## Geometry

During a rebase:

```
              (rh)
        A---B---C---D---E  (ORIG_HEAD, `oh`)
       /
  F---G---H---I  (onto, `ot`)
    (mb)    \
             A'--B'  (HEAD, mid-rebase)
```

| Ref | Alias | Description |
|-----|-------|-------------|
| merge-base | `mb` | Where feature diverged (G) |
| ORIG_HEAD | `oh` | Original feature tip (E) |
| onto | `ot` | Commit rebasing onto (I) |
| REBASE_HEAD | `rh` / `rbh` | Commit being replayed (C) |
| HEAD | - | Current position (B') |

## Refspec Range Aliases

| Alias | Range | Use case |
|-------|-------|----------|
| `mboh` | `mb..oh` | All original feature commits |
| `mbot` | `mb..ot` | Upstream changes since diverge |
| `mbrh` | `mb..rh` | Original commits up to current (inclusive) |
| `mbrhp` / `mbrp` | `mb..rh^` | Original commits processed so far |
| `oth` | `ot..HEAD` | Replayed commits so far |
| `rprh` | `rh^..rh` | Current commit being replayed |
| `crs <ref>` | `ref^..ref` | Expand any ref to single-commit range |

## Comparison Pairs

Three useful pairs for [git-didi] comparisons:

1. **Feature vs upstream** — what changed on each side since diverge
   ```bash
   gddp `mboh` `mbot`
   ```

2. **Mid-rebase progress** — verify commits replay correctly
   ```bash
   gddp `mbrhp` `oth`
   ```

3. **Post-rebase verification** — confirm all changes preserved
   ```bash
   gddp `mboh` `oth`
   ```

## With Pipeline Commands

For binary files like Parquet:

```bash
gddp `mboh` `oth` pqa -p data.parquet
```

## Smart `git mb`

The `mb` command auto-detects rebase/merge state:

```bash
git mb              # In rebase: merge-base(oh, ot)
                    # In merge: merge-base(HEAD, MERGE_HEAD)
git mb main HEAD    # Pass-through to git merge-base
```

[git-didi]: https://github.com/ryan-williams/git-didi

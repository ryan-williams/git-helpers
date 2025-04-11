#!/usr/bin/env python
#
# Wrapper around `gh run list`, supporting:
#
# - Comma-delimited, fuzzy-matched lists of:
#   - Run "status" values (-s/--status)
#   - JSON fields to return (-j/--json)
#   - Workflow-file basenames (positional args)
# - Filtering

import json
import re
from os.path import basename
from subprocess import DEVNULL
from sys import stdout
from typing import Literal, get_args, TypeVar, Callable

from click import command, option, BadParameter, argument
from utz import proc, silent, err, parallel, Log, solo
from utz.cli import flag, inc_exc, multi
from utz.rgx import Patterns

Status = Literal[
    'queued',
    'completed',
    'in_progress',
    'requested',
    'waiting',
    'pending',
    'action_required',
    'cancelled',
    'failure',
    'neutral',
    'skipped',
    'stale',
    'startup_failure',
    'success',
    'timed_out',
]
STATUSES = get_args(Status)


JsonField = Literal[
    'attempt',
    'conclusion',
    'createdAt',
    'databaseId',
    'displayTitle',
    'event',
    'headBranch',
    'headSha',
    'name',
    'number',
    'startedAt',
    'status',
    'updatedAt',
    'url',
    'workflowDatabaseId',
    'workflowName',
]
JSON_FIELDS = get_args(JsonField)


def is_subseq(subseq: str, seq: str) -> bool:
    """Return True if `subseq` is a subsequence of `seq`."""
    if not subseq:
        return True
    if not seq:
        return False
    if subseq[0] in seq:
        return is_subseq(subseq[1:], seq[seq.index(subseq[0]) + 1:])
    return False


T = TypeVar("T")


def parse_val(
    val: str,
    vals: list[T],
    err: Callable[[str], Exception],
) -> T:
    if val in vals:
        return val

    prefixes = [
        status
        for status in vals
        if status.startswith(val)
    ]
    if len(prefixes) == 1:
        return prefixes[0]
    elif len(prefixes) > 2:
        raise err(f"Status '{val}' is ambiguous; could be any of: {prefixes}")

    substrs = [
        status
        for status in vals
        if val in status
    ]
    if len(substrs) == 1:
        return substrs[0]
    elif len(substrs) > 2:
        raise err(f"Status '{val}' is ambiguous; could be any of: {substrs}")

    subseqs = [
        status
        for status in vals
        if is_subseq(val, status)
    ]
    if len(subseqs) == 1:
        return subseqs[0]
    elif len(subseqs) > 2:
        raise err(f"Status '{val}' is ambiguous; could be any of: {subseqs}")
    raise err(f"'{val}' not a subsequence of any of: {vals}")


def parse_vals(
    val: str | None,
    vals: list[T],
    err: Callable[[str], Exception],
) -> list[T]:
    if val is None:
        return []
    if val == '*':
        return vals
    lvals_map = { v.lower(): v for v in vals }
    lvals = list(lvals_map.keys())
    rvs = []
    for v in val.split(','):
        t = parse_val(v, lvals, err=err)
        rvs.append(lvals_map[t])
    return rvs


vals_cb = lambda vals: (
    lambda ctx, param, val: parse_vals(
        val,
        vals=vals,
        err=lambda msg: BadParameter(msg, ctx, param)
    )
)


def parse_workflow_basenames(
    val: str | None,
    log: Log = None,
) -> list[str | None]:
    if val is None:
        return [None]

    workflow_paths = proc.lines('gh workflow list --json path -q .[].path', log=log)
    workflow_basenames = [
        basename(workflow_path)
        for workflow_path in workflow_paths
        if workflow_path.startswith('.github/workflows/')
    ]

    return parse_vals(
        val,
        vals=workflow_basenames,
        err=ValueError,
    )


@command
@flag('-a', '--all-branches', help='Include runs from all branches')
@flag('-A', '--include-artifacts', help="Include `artifacts` as a JSON key; this isn't supported by `gh`, but is fetched separately and merged in to the output result")
@option('-b', '--branch', help='Filter to runs from this branch; by default, only runs corresponding to the current branch are returned')
@flag('-c', '--compact', help='In JSON-output mode, output JSONL (with each run object on a single line)')
@flag('-i', '--ids-only', help='Only print IDs of matching runs, one per line')
@option('-j', '--json', 'json_fields', callback=vals_cb(JSON_FIELDS), help="Comma-delimited list of JSON fields to fetch; `*` or `-` for all fields")
@option('-L', '--limit', type=int, help='Maximum number of runs to fetch (passed through to `gh`; default 20)')
@inc_exc(
    multi('-n', '--name-includes', help="Filter to runs whose \"workflow name\" matches any of these regexs; comma-delimited, can also be passed multiple times"),
    multi('-N', '--name-excludes', help="Filter to runs whose \"workflow name\" doesn't match any of these regexs; comma-delimited, can also be passed multiple times"),
    'workflow_name_patterns',
    flags=re.I,
)
@option('-r', '--remote', help='Git remote to query')
@option('-s', '--status', 'statuses', callback=vals_cb(STATUSES), help="Comma-delimited list of statuses to query")
@flag('-v', '--verbose', help='Log subprocess commands as they are run')
@inc_exc(
    multi('-w', '--include-workflow-basenames', help='Comma-delimited list of workflow-file `basename` regexs to include'),
    multi('-W', '--exclude-workflow-basenames', help='Comma-delimited list of workflow-file `basename` regexs to exclude'),
    'workflow_basenames_patterns',
    flags=re.I,
)
@argument('ref', default='HEAD')
def main(
    all_branches: bool,
    include_artifacts: bool,
    branch: str | None,
    compact: bool,
    ids_only: bool,
    json_fields: list[JsonField],
    limit: int | None,
    workflow_name_patterns: Patterns,
    remote: str | None,
    statuses: list[Status],
    verbose: bool,
    workflow_basenames_patterns: Patterns,
    ref: str,
):
    """Wrapper around `gh run list`, supporting multiple values and fuzzy-matching for several flags."""
    log = err if verbose else silent
    if not remote:
        remote = proc.line('git default-remote', log=log)

    workflow_basenames = [
        workflow_basename
        for workflow_path in proc.lines('gh workflow list --json path -q .[].path', log=log)
        if workflow_path.startswith('.github/workflows/')
           and workflow_basenames_patterns(workflow_basename := basename(workflow_path))
    ] if workflow_basenames_patterns else [None]

    if not all_branches:
        if branch:
            refs = branch.split(',')
        else:
            prefix = f"{remote}/"
            refs = [
                branch[len(prefix):]
                for branch in proc.lines('git', 'branch', '--format=%(refname:short)', '-r', '--points-at', ref, log=log)
                if branch.startswith(f"{remote}/")
            ]
    else:
        refs = [None]

    if workflow_name_patterns:
        if 'workflowName' not in json_fields:
            json_fields.append('workflowName')

    if ids_only or include_artifacts:
        if 'databaseId' not in json_fields:
            json_fields.append('databaseId')

    def run_list(
        status: Status | None,
        ref: str | None,
        workflow_basename: str | None,
    ):
        cmd = [
            'gh', 'run', 'list',
            *(['-b', ref] if ref else []),
            *(['-L', str(limit)] if limit else []),
            *(['-s', status] if status else []),
            *(['-w', workflow_basename] if workflow_basename else []),
        ]
        kwargs = dict(
            log=log,
            stderr=None if verbose else DEVNULL,
        )
        if json_fields:
            return proc.json(
                *cmd,
                '--json', ','.join(json_fields),
                **kwargs,
            )
        else:
            proc.run(*cmd, **kwargs)

    statuses = statuses or [None]
    runs = parallel(
        [
            dict(status=status, ref=ref, workflow_basename=workflow_name)
            for status in statuses
            for ref in refs
            for workflow_name in workflow_basenames
        ],
        lambda obj: run_list(**obj),
        n_jobs=len(statuses) * len(refs) * len(workflow_basenames),
    )

    if json_fields:
        runs = [
            run
            for res in runs
            for run in res
            if 'workflowName' not in run or workflow_name_patterns(run['workflowName'])
        ]
        if include_artifacts:
            repo = proc.line('gh repo view --json nameWithOwner -q .nameWithOwner')
            runs = parallel(
                runs,
                # TODO: paginate
                lambda run: { **run, 'artifacts': proc.json(f'gh api repos/{repo}/actions/runs/{run["databaseId"]}/artifacts')['artifacts'] }
            )
        if ids_only and not include_artifacts:
            for run in runs:
                print(run['databaseId'])
        elif compact:
            for run in runs:
                json.dump(run, stdout)
                print()
        elif limit == 1:
            run = solo(runs)
            json.dump(run, stdout, indent=2, )
            print()
        else:
            json.dump(runs, stdout, indent=2)


if __name__ == '__main__':
    main()


"""Handy regexs for parsing git-command outputs."""

normal_refname_regex = "[a-zA-Z0-9-_/\.+]+"
refname_or_tag_regex = "(?:(?:HEAD -> )?%s|tag: %s)" % (normal_refname_regex, normal_refname_regex)
detached_refname_regex = "\((?:HEAD )?detached (?:from|at) %s\)" % normal_refname_regex
no_branch_regex = "\(no branch\)"
no_branch_rebase_regex = "\(no branch, rebasing %s\)" % normal_refname_regex
no_branch_bisect_regex = "\(no branch, bisect started on %s\)" % normal_refname_regex
combined_refname_regex = "|".join([
    normal_refname_regex,
    detached_refname_regex,
    no_branch_regex,
    no_branch_rebase_regex,
    no_branch_bisect_regex
])


def named(name, regex):
    return "(?P<%s>%s)" % (name, regex)


def refname_regex(name):
    return named(name, combined_refname_regex)


def captured_whitespace_regex(name):
    return named(name, '\s+')


hash_regex = named("hash", "[0-9a-f]+")


normal_refname_regex = "[a-zA-Z0-9-_/\.]+"
detached_refname_regex = "\(detached from %s\)" % normal_refname_regex
no_branch_regex = "\(no branch, rebasing %s\)" % normal_refname_regex
combined_refname_regex = "%s|%s|%s" % (
    normal_refname_regex, detached_refname_regex, no_branch_regex)


def named(name, regex):
    return "(?P<%s>%s)" % (name, regex)


def refname_regex(name):
    return named(name, combined_refname_regex)


def captured_whitespace_regex(name):
    return named(name, '\s+')


hash_regex = named("hash", "[0-9a-f]+")

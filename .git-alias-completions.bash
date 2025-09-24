#!/usr/bin/env bash
#
# Bash completions for git aliases
#

# Source git completions if not already loaded
if ! declare -f __git_complete &>/dev/null; then
    # Try to source git-completion.bash
    for completion_file in \
        /usr/share/bash-completion/completions/git \
        /usr/local/share/bash-completion/completions/git \
        /opt/homebrew/share/bash-completion/completions/git \
        ~/.git-completion.bash \
        "$(dirname "${BASH_SOURCE[0]}")/.git-completion.bash"; do
        if [ -f "$completion_file" ]; then
            source "$completion_file"
            break
        fi
    done
fi

# Only set up completions if __git_complete is available
if declare -f __git_complete &>/dev/null; then
    # Use __git_complete for standard git alias completions
    __git_complete gco _git_checkout
    __git_complete gb _git_branch
    __git_complete gd _git_diff
    __git_complete gl _git_log
    __git_complete gs _git_status
    __git_complete ga _git_add
    __git_complete gm _git_merge
    __git_complete gp _git_push
    __git_complete gf _git_fetch
    __git_complete gr _git_rebase

    # grh - git reset --hard (custom completion)
    _grh_completion() {
        local cur words cword prev
        _get_comp_words_by_ref -n =: cur words cword prev

        # Complete with git refs (branches, tags, commits)
        __gitcomp_nl "$(__git_refs)"
    }

    # gbc - git branch-reset -c (custom completion)
    _gbc_completion() {
        local cur words cword prev
        _get_comp_words_by_ref -n =: cur words cword prev

        # First argument: branch name
        if [ $cword -eq 1 ]; then
            __gitcomp_nl "$(__git_heads)"
        # Second argument: ref to reset to
        elif [ $cword -eq 2 ]; then
            __gitcomp_nl "$(__git_refs)"
        fi
    }

    # Register custom completions using __git_func_wrap pattern
    __git_complete grh grh_completion
    __git_complete gbc gbc_completion
fi

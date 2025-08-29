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

# grh - git reset --hard (accepts refs)
_grh_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"

    # Complete with git refs (branches, tags, commits)
    __gitcomp_nl "$(__git_refs)"
}

# gbc - git branch-reset -c (accepts branch name then ref)
_gbc_completion() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local prev="${COMP_WORDS[COMP_CWORD-1]}"

    # First argument: branch name
    if [ $COMP_CWORD -eq 1 ]; then
        __gitcomp_nl "$(__git_heads)"
    # Second argument: ref to reset to
    elif [ $COMP_CWORD -eq 2 ]; then
        __gitcomp_nl "$(__git_refs)"
    fi
}

# gco - git checkout (accepts branches, refs, files)
_gco_completion() {
    # Use git's built-in checkout completion
    _git_checkout
}

# Register completions
complete -F _grh_completion grh
complete -F _gbc_completion gbc
complete -F _gco_completion gco

# Also register for the 'g' prefixed versions if they exist
if type -t g &>/dev/null; then
    # For commands that go through 'g' wrapper
    _g_completion() {
        local cur="${COMP_WORDS[COMP_CWORD]}"
        local cmd="${COMP_WORDS[1]}"

        case "$cmd" in
            rh)
                # Simulate grh completion
                COMP_WORDS[0]="grh"
                unset 'COMP_WORDS[1]'
                COMP_WORDS=("${COMP_WORDS[@]}")
                ((COMP_CWORD--))
                _grh_completion
                ;;
            bc)
                # Simulate gbc completion
                COMP_WORDS[0]="gbc"
                unset 'COMP_WORDS[1]'
                COMP_WORDS=("${COMP_WORDS[@]}")
                ((COMP_CWORD--))
                _gbc_completion
                ;;
            co)
                # Simulate gco completion
                COMP_WORDS[0]="gco"
                unset 'COMP_WORDS[1]'
                COMP_WORDS=("${COMP_WORDS[@]}")
                ((COMP_CWORD--))
                _gco_completion
                ;;
        esac
    }
fi

# Clone a repo (including submodules), add it to `$PATH`, and `source` files of the form `.*rc`.
#
# This script is meant to be `source`d itself, and is not directly executable. Common usage pattern:
#
# ```bash
# # Install "dotfiles" repo `runsascoded/.rc` (from GitHub) on a fresh machine:
# . <(curl -L https://j.mp/_rc) runsascoded/.rc
#
# # If the repo passed has 2 or more slashes, or begins with gitlab.com, it's assumed to be a GitLab path:
# . <(curl -L https://j.mp/_rc) runsascoded/rc/py
# . <(curl -L https://j.mp/_rc) gitlab.com/runsascoded/rc
# ```

usage() {
  echo "$@" >&2
  cat >&2 <<EOF
Usage:

  $0 [-i] [-b branch] [-s init_script] <URL or github group/repo> [dest]

Flags:
-i "clone" the repository in-place (into the current directory)
-b git branch to clone and initialize
-s initial script to source in the clone (default: everything matching .*rc
EOF
  return 1
}

declare -a args
branch=
inplace=
jobs=8
remote=
script=
dest=

while [ $# -gt 0 ]
do
    unset OPTIND
    unset OPTARG
    while getopts ":b:ij:r:s:" opt
    do
      case "$opt" in
        b) branch="$OPTARG";;
        i) inplace=1;;
        j) jobs="$OPTARG";;
        r) remote="$OPTARG";;
        s) script="$OPTARG";;
        *) ;;
      esac
    done
    shift $((OPTIND-1))
    args+=("$1")
    shift
done

set -- "${args[@]}"
echo "Found $# positional args" >&2
if [ $# -eq 0 ]; then
  usage "No positional args found"
else
  url="$1"; shift
  if [ "${url#git@}" != "$url" ] || [ "${url#https://}" != "$url" ]; then
    # $url appears to be a full git URL already
    :
  else
    # Otherwise, parse `$url` as a repo path for GitHub (1 slash) or GitLab (2 or more slashes, or begins with "gitlab.com")
    num_slashes="$(tr -cd '/' <<< "$url" | wc -c)"
    if [[ $url =~ ^github.com ]]; then
      url="https://$url"
      echo "Inferred GitHub URL: $url" >&2
    elif [[ $url =~ ^gitlab.com ]]; then
      url="https://$url"
      echo "Inferred GitLab URL: $url" >&2
    elif [ "$num_slashes" -ge 2 ]; then
      url="https://gitlab.com/$url"
      echo "Inferred GitLab URL: $url" >&2
    elif [ "$num_slashes" -eq 1 ]; then
      url="https://github.com/$url"
      echo "Inferred GitHub URL: $url" >&2
    else
      echo "Unrecognized GitHub/GitLab repo path: $url" >&2
      return 1
    fi
  fi
  if [ $# -eq 2 ]; then
    dest="$1"; shift
  elif [ $# -gt 2 ]; then
    usage "Too many positional args ($# extra)"
  fi
fi

if [ -z "$remote" ]; then
  remote="$(git config clone.defaultRemoteName || true)"
  remote="${remote:-upstream}"
fi
if [ -z "$inplace" ]; then
  dir="${url%.git}"
  dir="${dir##*/}"
  echo "Cloning $url to $dir" >&2
  if [ -z "$dest" ]; then
    git clone -j "$jobs" "$url"
  else
    git clone -j "$jobs" "$url" "$dest"
  fi

  pushd "$dir" || return 2
  if [ -n "$branch" ]; then
    echo "Checking out branch $branch" >&2
    git checkout "$branch"
  fi
  git submodule update --init --recursive --jobs "$jobs" || return 100 2>/dev/null || return 100
  popd || return 3

  if [ -z "$script" ]; then
    script=".*rc"
  fi
else
  echo "\"Cloning\" $url in-place" >&2
  git init
  remote="upstream"
  git remote add "$remote" "$url" || echo "Found existing remote \"$remote\"" >&2
  git fetch "$remote" --recurse-submodules

  # Helper for backing up any files already present that would conflict with the git checkout (and cause it to abort)
  bak() {
    for arg in "$@"; do
      if [ -e "$arg" ]; then
        echo "Backing up $arg to $arg.bak" >&2
        mv "$arg" "$arg.bak"
      fi
    done
  }
  export -f bak

  branch="${branch:-master}"

  git ls-tree -r -z --name-only "$remote/$branch" | xargs -0 bash -c 'bak "$@"' _
  unset bak

  echo "Checking out branch $branch" >&2
  git checkout "$branch"
  git submodule update --init --recursive --jobs "$jobs"
fi

if [ -n "$script" ]; then
  cmd="for f in \"$PWD/$dir\"/$script; do . \$f; done"
  echo "Appending '$cmd' to .bashrc" >&2
  echo "$cmd" >> ~/.bashrc
  cmd="export PATH=\"$PWD/$dir:\$PATH\""
  echo "Appending '$cmd' to .bashrc" >&2
  echo "$cmd" >> ~/.bashrc
fi

. "$HOME/.bashrc"

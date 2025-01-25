#!/usr/bin/env bash

declare -a args

branch=
inplace=
jobs=8
remote=upstream
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

usage() {
  echo "$@" >&2
  cat <<EOF >&2
Usage:

  $0 [-i] [-b branch] [-s init_script] <URL or github group/repo> [dest]

Flags:
-i "clone" the repository in-place (into the current directory)
-b git branch to clone and initialize
-s initial script to source in the clone (default: everything matching .*rc
EOF
  exit 1
}

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
    # Otherwise, assume github.com and HTTPS protocol
    url="https://github.com/$url"
  fi
  if [ $# -eq 2 ]; then
    dest="$1"; shift
  elif [ $# -gt 2 ]; then
    usage "Too many positional args ($# extra)"
  fi
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

  pushd "$dir" || exit 2
  if [ -n "$branch" ]; then
    echo "Checking out branch $branch" >&2
    git checkout "$branch"
  fi
  git submodule update --init --recursive --jobs "$jobs" || return 100 2>/dev/null || exit 100
  popd || exit 3

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

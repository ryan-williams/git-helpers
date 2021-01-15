#!/usr/bin/env bash

declare -a ARGS

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
    ARGS+=("$1")
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

nargs=${#ARGS[@]}
echo "Found $nargs positional args"
if [ $nargs -eq 0 ]; then
  usage "No positional args found"
else
  url="${ARGS[0]}"
  ARGS=("${ARGS[@]:1}")
  if [ "${url#git@}" != "$url" ] || [ "${url#https://}" != "$url" ]; then
    # $url appears to be a full git URL already
    :
  else
    # otherwise, assume github.com and HTTPS protocol
    url="https://github.com/$url"
  fi
  if [ $nargs -eq 2 ]; then
    dest="${ARGS[0]}"
    ARGS=("${ARGS[@]:1}")
  elif [ $nargs -gt 2 ]; then
    usage "Too many positional args"
  fi
fi

if [ -z "$inplace" ]; then
  dir="${url%.git}"
  dir="${dir##*/}"
  echo "Cloning $url to $dir"
  if [ -z "$dest" ]; then
    git clone -j "$jobs" "$url"
  else
    git clone -j "$jobs" "$url" "$dest"
  fi

  pushd "$dir" || exit 2
  if [ -n "$branch" ]; then
    echo "Checking out branch $branch"
    git checkout "$branch"
  fi
  git submodule update --init --recursive --jobs "$jobs" || return 100 2>/dev/null || exit 100
  popd || exit 3

  if [ -z "$script" ]; then
    script=".*rc"
  fi
else
  echo "\"Cloning\" $url in-place"
  git init
  remote="upstream"
  git remote add "$remote" "$url" || echo "Found existing remote \"$remote\""
  git fetch "$remote" --recurse-submodules

  # Helper for backing up any files already present that would conflict with the git checkout (and cause it to abort)
  bak() {
    for arg in "$@"; do
      if [ -e "$arg" ]; then
        echo "Backing up $arg to $arg.bak"
        mv "$arg" "$arg.bak"
      fi
    done
  }
  export -f bak

  branch="${branch:-master}"

  git ls-tree -r -z --name-only "$remote/$branch" | xargs -0 bash -c 'bak "$@"' _
  unset bak

  echo "Checking out branch $branch"
  git checkout "$branch"
  git submodule update --init --recursive --jobs "$jobs"
fi

if [ -n "$script" ]; then
  echo "Appending \"source $PWD/$dir/$script\" to .bashrc"
  echo "source $PWD/$dir/$script" >> ~/.bashrc
fi

. ~/.bashrc

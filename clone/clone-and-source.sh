#!/usr/bin/env bash

declare -a ARGS

branch=
inplace=
remote=upstream
script=
dest=

while [ $# -gt 0 ]
do
    unset OPTIND
    unset OPTARG
    while getopts ":b:ir:s:" opt
    do
      case "$opt" in
        b) branch="$OPTARG";;
        i) inplace=1;;
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
  if [ -n "${url%%https://*}" ]; then
    url="git@github.com:$url.git"
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
    git clone "$url"
  else
    git clone "$url" "$dest"
  fi

  pushd "$dir"
  if [ -n "$branch" ]; then
    echo "Checking out branch $branch"
    git checkout "$branch"
  fi
  git submodule update --init --recursive
  popd

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
  git submodule update --init --recursive
fi

if [ -n "$script" ]; then
  echo "Appending \"source $dir/$script\" to .bashrc"
  echo "source $dir/$script" >> ~/.bashrc
fi

. .bashrc

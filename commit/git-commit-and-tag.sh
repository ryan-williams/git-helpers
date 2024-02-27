#!/usr/bin/env bash

tag=${@: -1}
set -- "${@:1:$#-1}"
if [ "${@: -1}" == "-f" ]; then
    force=(-f)
    set -- "${@:1:$#-1}"
else
    force=()
fi
git commit "$@" -m "$tag"
git tag "${force[@]}" "$tag"

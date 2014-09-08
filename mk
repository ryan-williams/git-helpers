#!/bin/sh

args=''
root=$(git-root -v)
echo $root
relpath=$(git-relpath)
for arg in $@; do
    args=$args$relpath$arg" "
done

echo $args
make -C $root $args

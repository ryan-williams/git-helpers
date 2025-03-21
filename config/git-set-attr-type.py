#!/usr/bin/env python
#
# Manage "attr type" for one or more file extensions.
#
# Modify, remove, comment, or uncomment `.gitattributes` lines pertaining to filename-glob patterns:
#
# ```bash
# # *.ipynb diff=ipynb
# git set-attr-type.py -a diff ipynb  # a.k.a. `gsdt ipynb`
#
# # *.ipynb merge=nb
# git set-attr-type.py -a merge ipynb nb  # a.k.a. `gsmt ipynb nb`
#
# # *.ipynb diff=nb
# # *.ipynb merge=nb
# git set-attr-type.py -a diff,merge ipynb nb  # a.k.a. `gsdm ipynb nb`
#
# # "Unset" `diff` and `merge` keys for `*.ipynb` files:
# git set-attr-type.py -a diff,merge -u ipynb  # a.k.a. `gudm ipynb`
# ```
#
# Passing `-c/--comment-lines` will comment/uncomment lines matching the given blob, instead of modifying/removing in-place.

import re
from os import rename
from os.path import realpath, dirname, basename
from tempfile import NamedTemporaryFile

from click import command, argument, option
from utz import proc, err


@command
@option(
    '-a', '--attr', 'attrs', required=True,
    callback=lambda ctx, param, value: None if value is None else value.split(','),
    help='Attr-types to manipulate (e.g. `diff`, `merge`; comma-delimited)'
)
@option('-c', '--comment-lines', is_flag=True, help='Comment/Uncomment lines (instead of removing/modifying)')
@option('-u', '--unset', is_flag=True, help='')
@argument('extension')
@argument('name', required=False)
def main(
    attrs: tuple[str, ...] | None,
    comment_lines: bool,
    unset: bool,
    extension: str,
    name: str | None,
):
    """Manage "attr type" for one or more file extensions."""
    if not attrs:
        err(f"Pass one or more (comma-delimited) attr-types as `-a/--attr`")

    if unset:
        if name:
            raise ValueError(f"Pass -u/--unset xor <name>")
    elif not name:
        name = extension

    attrs_file = proc.line('git', 'config', 'core.attributesfile')
    attrs_dir = dirname(realpath(attrs_file))
    with open(attrs_file, 'r') as f:
        lines = [ line.rstrip('\n') for line in f.readlines() ]

    attrs_group = r'(?P<attr>%s)' % '|'.join(attrs)
    rgx = re.compile(r'(?P<comment>#\s*)?(?P<pattern>\*\.%s)\s+%s=(?P<name>\w+)(?P<suffix>.*)' % (extension, attrs_group))
    with NamedTemporaryFile(dir=attrs_dir, prefix=basename(attrs_file), delete=False) as tmp_file:
        tmp_path = tmp_file.name
        with open(tmp_path, 'w') as f:
            founds = set()
            for idx, line in enumerate(lines):
                lineno = idx + 1

                def log(msg: str):
                    err(f"{lineno}: {msg}")

                m = rgx.fullmatch(line)
                if m:
                    attr = m['attr']
                    found = attr in founds
                    comment = m['comment']
                    if name and m['name'] == name:
                        if comment:
                            if found:
                                if comment_lines:
                                    log(f"leaving extra match commented: {line}")
                                else:
                                    log(f"removing extra match commented: {line}")
                                    continue
                            else:
                                log(f"uncommenting line: {line}")
                                line = line[len(comment):]
                                founds.add(attr)
                        else:
                            if found:
                                if comment_lines:
                                    log(f"commenting extra match: {line}")
                                else:
                                    log(f"removing extra match: {line}")
                                    continue
                            else:
                                log(f"found line: {line}")
                                founds.add(attr)
                    else:
                        if comment:
                            if comment_lines:
                                log(f"leaving line commented: {line}")
                            else:
                                log(f"removing commented line: {line}")
                                continue
                        else:
                            if comment_lines:
                                log(f"commenting line: {line}")
                                line = f'# {line}'
                            else:
                                log(f"removing line: {line}")
                                continue

                print(line, file=f)

            if name:
                for attr in attrs:
                    if attr not in founds:
                        line = f"*.{extension} {attr}={name}"
                        err(f"Appending line: {line}")
                        print(line, file=f)

        rename(tmp_path, attrs_file)


if __name__ == "__main__":
    main()

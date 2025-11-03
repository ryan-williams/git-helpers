#!/usr/bin/env bash
# Test script to display gddp color swatches for all 6 nested diff patterns

cat << 'EOF'
gddp Color Swatches (256-color palette for dark terminals)
===========================================================

The 6 patterns in diff-of-diffs output:

EOF

# ++ pattern - Added line in added section (white on dark green, bold)
echo -e "\033[1;38;5;231;48;5;22m++ Added line in added section (white on dark green, bold)\033[0m"
echo -e "\033[1;38;5;231;48;5;22m++version = \"11.1.0\"\033[0m"
echo

# -- pattern - Removed line in removed section (white on dark red, bold)
echo -e "\033[1;38;5;231;48;5;52m-- Removed line in removed section (white on dark red, bold)\033[0m"
echo -e "\033[1;38;5;231;48;5;52m--version = \"11.0.0\"\033[0m"
echo

# +<space> pattern - Context line in added section (white on dark green)
echo -e "\033[38;5;231;48;5;22m+  Context line in added section (white on dark green)\033[0m"
echo -e "\033[38;5;231;48;5;22m+ source = { registry = \"https://pypi.org/simple\" }\033[0m"
echo

# -<space> pattern - Context line in removed section (white on dark red)
echo -e "\033[38;5;231;48;5;52m-  Context line in removed section (white on dark red)\033[0m"
echo -e "\033[38;5;231;48;5;52m- source = { registry = \"https://pypi.org/simple\" }\033[0m"
echo

# +- pattern - Added line in removed section (bright green on dark red)
echo -e "\033[38;5;46;48;5;52m+- Added line appears in removed section (bright green on dark red)\033[0m"
echo -e "\033[38;5;46;48;5;52m+-    { name = \"new-dependency\" },\033[0m"
echo

# -+ pattern - Removed line in added section (bright red on dark green)
echo -e "\033[38;5;196;48;5;22m-+ Removed line appears in added section (bright red on dark green)\033[0m"
echo -e "\033[38;5;196;48;5;22m-+    { name = \"old-dependency\" },\033[0m"
echo

cat << 'EOF'
Color codes used:
-----------------
Foreground: 231 (white), 46 (bright green), 196 (bright red)
Background: 22 (dark green), 52 (dark red/maroon)

Usage: Run `gddp <range1> <range2>` to see these in action
EOF

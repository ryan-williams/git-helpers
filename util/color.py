#!/usr/bin/python

import re

# Adapted from Bash colors helper script by Mike Stewart -
# http://MediaDoneRight.com
colors = {
    # Reset
    "Color_Off": "\x1b[0m",       # Text Reset
    "COff": "\x1b[0m",
    "clear": "\x1b[0m",

    # Regular Colors
    "Black": "\x1b[0;30m",        # Black
    "Red": "\x1b[0;31m",          # Red
    "Green": "\x1b[0;32m",        # Green
    "Yellow": "\x1b[0;33m",       # Yellow
    "Blue": "\x1b[0;34m",         # Blue
    "Purple": "\x1b[0;35m",       # Purple
    "Cyan": "\x1b[0;36m",         # Cyan
    "White": "\x1b[0;37m",        # White

    # Bold
    "BBlack": "\x1b[1;30m",       # Black
    "BRed": "\x1b[1;31m",         # Red
    "BGreen": "\x1b[1;32m",       # Green
    "BYellow": "\x1b[1;33m",      # Yellow
    "BBlue": "\x1b[1;34m",        # Blue
    "BPurple": "\x1b[1;35m",      # Purple
    "BCyan": "\x1b[1;36m",        # Cyan
    "BWhite": "\x1b[1;37m",       # White

    # Underline
    "UBlack": "\x1b[4;30m",       # Black
    "URed": "\x1b[4;31m",         # Red
    "UGreen": "\x1b[4;32m",       # Green
    "UYellow": "\x1b[4;33m",      # Yellow
    "UBlue": "\x1b[4;34m",        # Blue
    "UPurple": "\x1b[4;35m",      # Purple
    "UCyan": "\x1b[4;36m",        # Cyan
    "UWhite": "\x1b[4;37m",       # White

    # Background
    "On_Black": "\x1b[40m",       # Black
    "On_Red": "\x1b[41m",         # Red
    "On_Green": "\x1b[42m",       # Green
    "On_Yellow": "\x1b[43m",      # Yellow
    "On_Blue": "\x1b[44m",        # Blue
    "On_Purple": "\x1b[45m",      # Purple
    "On_Cyan": "\x1b[46m",        # Cyan
    "On_White": "\x1b[47m",       # White

    # High Intensty
    "IBlack": "\x1b[0;90m",       # Black
    "IRed": "\x1b[0;91m",         # Red
    "IGreen": "\x1b[0;92m",       # Green
    "IYellow": "\x1b[0;93m",      # Yellow
    "IBlue": "\x1b[0;94m",        # Blue
    "IPurple": "\x1b[0;95m",      # Purple
    "ICyan": "\x1b[0;96m",        # Cyan
    "IWhite": "\x1b[0;97m",       # White

    # Bold High Intensty
    "BIBlack": "\x1b[1;90m",      # Black
    "BIRed": "\x1b[1;91m",        # Red
    "BIGreen": "\x1b[1;92m",      # Green
    "BIYellow": "\x1b[1;93m",     # Yellow
    "BIBlue": "\x1b[1;94m",       # Blue
    "BIPurple": "\x1b[1;95m",     # Purple
    "BICyan": "\x1b[1;96m",       # Cyan
    "BIWhite": "\x1b[1;97m",      # White

    # High Intensty backgrounds
    "On_IBlack": "\x1b[0;100m",   # Black
    "On_IRed": "\x1b[0;101m",     # Red
    "On_IGreen": "\x1b[0;102m",   # Green
    "On_IYellow": "\x1b[0;103m",  # Yellow
    "On_IBlue": "\x1b[0;104m",    # Blue
    "On_IPurple": "\x1b[10;95m",  # Purple
    "On_ICyan": "\x1b[0;106m",    # Cyan
    "On_IWhite": "\x1b[0;107m",   # White
}


def color_symbol(name):
    return colors[name]


def color(name, s=None, cond=True):
    if s == None:
        return color_symbol(name)
    if cond:
        return color_symbol(name) + s + color_symbol('COff')
    return s

color_char_regex = '\x1b' + '\[(?:[0-9];)?[0-9]+m'


def clen(s):
    return len(re.sub(color_char_regex, '', str(s)))

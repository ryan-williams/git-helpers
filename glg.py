#!/usr/bin/python

import gitpython
import subprocess
import sys

if len(sys.argv) < 2:
    print "Specify a file to match"
    sys.exit(1)

pattern = sys.argv[1]
print pattern

ls = subprocess.Popen(['git', 'ls-files'], stdout=subprocess.PIPE).stdout
choices = subprocess.Popen(
    ['grep', pattern], stdin=ls, stdout=subprocess.PIPE).stdout.read()

print choices


def getChoice(choices):
    if len(choices) == 1:
        choices[0]

    while True:
        print "Found matches"
        for i in range(len(choices)):
            print "\t%d)\t%s" % (i, choices[i])
        choice = input("Choose one: ")
        try:
            choiceNum = int(choice)
            if 0 <= choiceNum and choiceNum < len(choices):
                break
        except:
            print "Invalid choice"
    return choices[choice]

choice = getChoice(choices)

# print subprocess.Popen(['git', 'log', '-p', '--follow', '--', choice],
# stdout=subprocess.PIPE).stdout.read()

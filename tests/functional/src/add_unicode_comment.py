# -*- coding: utf-8 -*-
#
# -----------------------------------------------------------------------------
#                     The CodeChecker Infrastructure
#   This file is distributed under the University of Illinois Open Source
#   License. See LICENSE.TXT for details.
# -----------------------------------------------------------------------------

import argparse
import os
import re

commentBegin = '/* Unicode comment\n'
commentEnd = '\nUnicode comment */'

comment = \
r"""Hungarian special characters:
áÁ éÉ íÍ óÓ öÖ őŐ úÚ üÜ űŰ

Other special characters:
äÄ åÅ àÀ âÂ æÆ çÇ èÈ êÊ ëË îÎ ïÏ ôÔ œŒ ß ùÙ ûÛ ÿŸ"""

# somebody might have written into the line directly after the comment, if so do not remove '\n'
commentPattern = re.compile(r'\n' + re.escape(commentBegin) + r'.*?' + re.escape(commentEnd) + r'(\n(?=\n|$))?', re.DOTALL)

def parseArgs():
    global args
    parser = argparse.ArgumentParser(description = \
        'This script appends a C block comment containing special Unicode characters to the end of the source files.')

    parser.add_argument('--remove', '-r', action='store_true', dest='remove',
        help='Remove the comments from the files.')

    parser.add_argument(dest='paths', nargs='*',
        help='The paths of the source files or the directories containing the source files. Directories are explored recursively.')

    args = parser.parse_args()

def addCommentToFile(filePath):
    if args.remove:
        print('Removing comments from %s' % filePath)
        fullComment = ''
    else:
        print('Adding the comment to %s' % filePath)
        fullComment = '\n' + commentBegin + comment + commentEnd + '\n'

    with open(filePath, 'r+') as file:
        text = file.read()
        text = re.sub(commentPattern, '', text)
        text += fullComment

        file.seek(0)
        file.truncate()
        file.write(text)

def addCommentToDirectory(dirPath):
    for root, subFolders, files in os.walk(dirPath):
        for fileName in files:
            if not re.match(r'.*(\.c|\.h|\.cpp|\.hpp|\.cxx|\.hxx)$', fileName):
                continue
            filePath = os.path.join(root, fileName)
            addCommentToFile(filePath)

def main():
    parseArgs()
    if len(args.paths) > 0:
        for path in args.path:
            fullPath = os.path.realpath(path)
            if os.path.isfile(fullPath):
                addCommentToFile(fullPath)
            elif os.path.isdir(fullPath):
                addCommentToDirectory(fullPath)
            else:
                print('%s is not a valid file or directory.' % path)
    else:
        workingDir = os.getcwd()
        addCommentToDirectory(workingDir)

if __name__ == '__main__':
    main()

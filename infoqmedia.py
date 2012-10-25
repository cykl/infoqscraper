#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
infoqmedia.py
Copyright (c) 2012, Clément MATHIEU
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
 * Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


import infoq
import os
import argparse
import sys
import subprocess
import re


def check_dependencies(bins):
    ok = True
    for cmd in bins:
        try:
            with open(os.devnull, 'w') as null:
                subprocess.call(cmd, stdout=null, stderr=null)
        except OSError:
            print >> sys.stderr, "%s not found. Please install required dependencies or specify the binary location" % (cmd)
            ok = False

    return ok

def extract_id(arg):
    mo = re.search("^https?://www.infoq.com/presentations/([^/])$", arg)
    if mo:
        return mo.group(1)
    else:
        return arg

def chose_output(output, id):
    if output:
        return output

    return u"%s.avi" % id

def main():
    parser = argparse.ArgumentParser(description='Download presentations from InfoQ.')
    parser.add_argument('-f', '--ffmpeg'   , nargs="?", type=str, default="ffmpeg",    help='ffmpeg binary')
    parser.add_argument('-s', '--swfrender', nargs="?", type=str, default="swfrender", help='swfrender binary')
    parser.add_argument('-r', '--rtmpdump' , nargs="?", type=str, default="rtmpdump" , help='rtmpdump binary')
    parser.add_argument('-o', '--output'   , nargs="?", type=str, help='output file')
#    parser.add_argument('-j', '--jpeg'     , action="store_true", help='Use JPEG rather than PNG (for buggy ffmpeg versions)')
#    parser.add_argument('-q', '--quiet'    , action='store_true', help='quiet mode')
#    parser.add_argument('-d', '--debug'    , action='store_true', help='debug mode')

    parser.add_argument('name', help='name of the presentation or url')

    args = parser.parse_args()

    # Check required tools are available before doing any useful workd
    if not check_dependencies([args.ffmpeg, args.swfrender, args.rtmpdump]):
        sys.exit(1)

    # Process arguments
    id = extract_id(args.name)
    output = chose_output(args.output, id)

    try:
        iq = infoq.InfoQ()
        try:
            presentation = infoq.Presentation(id, iq)
        except infoq.DownloadFailedException as e:
            print >> sys.stderr, "Presentation %s not found. Please check your id or url" % id
            return 1

        builder = infoq.OfflinePresentation(presentation,
            ffmpeg=args.ffmpeg,
            rtmpdump=args.rtmpdump,
            swfrender=args.swfrender
        )
        builder.create_presentation(output_path=args.output)
        return 0

    except  KeyboardInterrupt:
        print >> sys.stderr, "Aborted."

if __name__ == "__main__":
    sys.exit(main())

#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
infoqlisting.py
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

import re
import argparse
import sys

class _Filter(infoq.MaxPagesFilter):
    def __init__(self, pattern, max_hits=20, max_pages=5):
        super(_Filter, self).__init__(max_pages)

        self.pattern = pattern
        self.max_hits = max_hits
        self.hits = 0

    def filter(self, p_summary):
        if self.hits >= self.max_hits:
            raise StopIteration

        s = super(_Filter, self).filter(p_summary)
        if s and not self.pattern or re.search(self.pattern, p_summary['desc'] + " " + p_summary['title'], flags=re.I):
            self.hits += 1
            return s

def _standardOutput(results):
    from textwrap import fill

    index = 0
    for result in results:
        print
        print u"{0:>3}. Title: {1} ({2})".format(index, result['title'], result['date'].strftime("%Y-%m-%d"))
        print u"     Id: {0}".format(result['id'])
        print u"     Desc: \n{0}{1}".format(' ' * 8, fill(result['desc'], width=80, subsequent_indent=' ' * 8))
        index += 1

def _shortOutput(results):
    for result in results:
        print result['id']

def main():
    parser = argparse.ArgumentParser(description='List presentations available on InfoQ.')
    parser.add_argument('-m', '--max-pages', type=int, default=10,   help='maximum number of pages to retrieve (8 presentations per page)')
    parser.add_argument('-n', '--max-hits' , type=int, default=10,   help='maximum number of hits')
    parser.add_argument('-p', '--pattern'  , type=str, default=None, help='filter hits according to this pattern')
    parser.add_argument('-s', '--short'    , action="store_true",    help='short output, only ids are displayed')

    args = parser.parse_args()

    try:
        iq = infoq.InfoQ()
        f = _Filter(args.pattern, max_hits=args.max_hits, max_pages=args.max_pages)
        summaries = iq.presentation_summaries(filter=f)
        if args.short:
            _shortOutput(summaries)
        else:
            _standardOutput(summaries)


        return 0
    except  KeyboardInterrupt:
        print >> sys.stderr, "Aborted."

if __name__ == "__main__":
    sys.exit(main())

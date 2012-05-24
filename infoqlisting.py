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

import re
import urllib
import urllib2
import argparse
import sys

class InfoQLister:
    _baseUrl = "http://www.infoq.com/rightbar.action"

    _presentationPerPage = 8

    _titleRegexp = re.compile("href=\"/presentations/(?P<id>.*);jsessionid=.*\">(?P<title>.*)</a>")
    _descRegexp  = re.compile("<p>(?P<desc>.*?)</p>.*?<ul class=\"info link-col\">", flags=re.M|re.S)

    def __init__(self):
        pass

    @staticmethod
    def _fetchPage(index):
        params   = urllib.urlencode({"language": "en", "selectedTab": "PRESENTATION", "startIndex": index})
        request  = urllib2.Request(InfoQLister._baseUrl, data=params)
        response = urllib2.urlopen(request)
        data = response.read()
        return data

    @staticmethod
    def _parsePage(index):
        data = InfoQLister._fetchPage(index)

        presentations = []

        blocks =  re.findall("<div class=\"entry\" id=\"entry[0-9]+\">.*?<ul class=\"info link-col\">", data, flags=re.M|re.S)
        for block in blocks:
            presentation = {}
            groups = InfoQLister._titleRegexp.search(block)
            presentation['id'] = groups.groupdict()['id']
            presentation['title']= groups.groupdict()['title']

            groups = InfoQLister._descRegexp.search(block)
            presentation['desc'] = groups.groupdict()['desc']

            presentations.append(presentation)

        return presentations

    def search(self, pattern, maxHits=20, maxPages=5):
        results = []

        page = 0
        while len(results) < maxHits and page < maxPages:
            presentations = self._parsePage(page * InfoQLister._presentationPerPage)
            for presentation in presentations:
                if not pattern or re.search(pattern, presentation['title'], flags=re.I):
                    results.append(presentation)
                    if len(results) == maxHits:
                        break

            page += 1

        return results

    def list(self, count=10):
        self.search(None, maxHits=10)


def _standardOutput(results):
    from textwrap import fill

    for index in xrange(len(results)):
        result = results[index]
        print
        print "{0:>3}. Title: {1}".format(index, result['title'])
        print "     Id: {0}".format(result['id'])
        print "     Desc: \n{0}{1}".format(' ' * 8, fill(result['desc'], width=80, subsequent_indent=' ' * 8))

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
        lister = InfoQLister()
        results =  lister.search(args.pattern, maxHits=args.max_hits, maxPages=args.max_pages)
        if args.short:
            _shortOutput(results)
        else:
            _standardOutput(results)


        return 0
    except  KeyboardInterrupt:
        print >> sys.stderr, "Aborted."

if __name__ == "__main__":
    sys.exit(main())

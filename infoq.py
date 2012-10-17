# -*- coding: UTF-8 -*-
"""InfoQ web client


Visit http;//www.infoq.com

"""
__version__ = "0.0.1-dev"
__license__ = """
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
__author__ = "Clément MATHIEU <clement@unportant.info>"
__contributors__ = [

]

import urllib, urllib2
import datetime
from cookielib import CookieJar
from bs4 import BeautifulSoup

# Number of presentation entries per page returned by rightbar.action
RIGHT_BAR_ENTRIES_PER_PAGES = 8

# InfoQ requires cookies to be logged in. Use a dedicated urllib opener
_http_client = urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieJar()))


def get_url(path, scheme="http"):
    """ Return the full InfoQ URL """
    return scheme + "://www.infoq.com" + path


class InfoQ:
    """ InfoQ web client entry point"""
    def __init__(self):
        self.authenticated = False

    def _login(self, username, password):
        """ Log in.

        An exception is raised if authentication fails.
        """
        url = get_url("/login.action", scheme="https")
        params = {
            'username': username,
            'password': password,
            'fromHeader': 'true',
            'submit-login': '',
        }
        response = _http_client.open(url, urllib.urlencode(params))
        if not "loginAction_ok.jsp" in response.url:
            raise Exception("Login failed")

        self.authenticated = True


    def presentation_summaries(self, filter=None):
        """ Generate presentation summaries in a reverse chronological order.

         A filter class can be supplied to filter summaries or bound the fetching process.
        """
        try:
            for page_index in xrange(1000):
                rb = RightBarPage(page_index)
                rb.fetch()
                for summary in rb.summaries():
                    if not filter or filter.filter(summary):
                        yield summary
        except StopIteration:
            pass


class MaxPagesFilter:
    """ A summary filter which bound the number fetched RightBarPage"""

    def __init__(self, max_pages):
        self.max_pages = max_pages
        self.seen = 0

    def filter(self, presentation_summary):
        if self.seen / RIGHT_BAR_ENTRIES_PER_PAGES >= self.max_pages:
            raise StopIteration

        self.seen += 1
        return presentation_summary


class RightBarPage:
    """A page returned by /rightbar.action

    This page lists all available presentations with pagination.
    """
    def __init__(self, index):
        self.index = index

    def fetch(self):
        """Download the page and create the soup"""

        params = {
            "language": "en",
            "selectedTab": "PRESENTATION",
            "startIndex": self.index,
        }
        response = _http_client.open(get_url("/rightbar.action"), urllib.urlencode(params))
        if response.getcode() != 200:
            raise Exception("Fetching rightbar index %s failed" % self.index)
        self.soup = BeautifulSoup(response.read())

    def summaries(self):
        """Return a list of all the presentation summaries contained in this page"""
        def create_summary(div):
            def get_id(div):
                return get_path(div).rsplit('/', 1)[1]

            def get_path(div):
                # remove session id if present
                return div.find('a')['href'].rsplit(';', 2)[0]

            def get_desc(div):
                return div.find('p', class_='image').find_next_sibling('p').get_text(strip=True)

            def get_auth(div):
                return div.find('a', class_='editorlink').get_text(strip=True)

            def get_date(div):
                # Some pages have a comma after the date
                str = div.find('a', class_='editorlink').parent.next_sibling.strip(" \t\n\r,")
                return datetime.datetime.strptime(str, "%b %d, %Y")

            def get_title(div):
                return div.find('h1').get_text().strip()

            return {
                'id'   : get_id(div),
                'path' : get_path(div),
                'desc' : get_desc(div),
                'auth' : get_auth(div),
                'date' : get_date(div),
                'title': get_title(div),
            }

        entries = self.soup.findAll('div', {'class': 'entry'})
        return [create_summary(div) for div in entries]

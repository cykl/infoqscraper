# -*- coding: UTF-8 -*-
"""InfoQ web client


Visit http;//www.infoq.com

"""
import base64
import os


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

import datetime
import urllib, urllib2
import re
from cookielib import CookieJar
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString

# Number of presentation entries per page returned by rightbar.action
RIGHT_BAR_ENTRIES_PER_PAGES = 8

def get_url(path, scheme="http"):
    """ Return the full InfoQ URL """
    return scheme + "://www.infoq.com" + path

def fetch(client, urls, dir_path):
    '''Download all the URLs in the specified directory.'''
    # TODO: Implement parallel download
    for url in urls:
        response = client.open(url)
        if response.getcode() != 200:
            raise Exception("Login failed")

        filename =  url.rsplit('/', 1)[1]

        with open(os.path.join(dir_path, filename), "w") as f:
            f.write(response.read())

class InfoQ(object):
    """ InfoQ web client entry point"""
    def __init__(self):
        self.authenticated = False
        # InfoQ requires cookies to be logged in. Use a dedicated urllib opener
        self.client = urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieJar()))

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
        response = self.client.open(url, urllib.urlencode(params))
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
                rb.fetch(self.client)
                for summary in rb.summaries():
                    if not filter or filter.filter(summary):
                        yield summary
        except StopIteration:
            pass


class MaxPagesFilter(object):
    """ A summary filter which bound the number fetched RightBarPage"""

    def __init__(self, max_pages):
        self.max_pages = max_pages
        self.seen = 0

    def filter(self, presentation_summary):
        if self.seen / RIGHT_BAR_ENTRIES_PER_PAGES >= self.max_pages:
            raise StopIteration

        self.seen += 1
        return presentation_summary

class Presentation(object):

    def __init__(self, id, client=urllib2.build_opener()):
        self.id = id
        self._soup = None
        self._metadata = None
        self.client = client

    def fetch(self):
        """Download the page and create the soup"""
        url = get_url("/presentations/" + self.id)
        response = self.client.open(url)
        if response.getcode() != 200:
            raise Exception("Fetching presentation %s failed" % url)
        return BeautifulSoup(response.read(), "html5lib")

    @property
    def soup(self):
        if not self._soup:
            self._soup = self.fetch()

        return self._soup

    @property
    def metadata(self):
        def get_title(bc3):
            return bc3.find('h1').find('a').get_text().strip()

        def get_date(bc3):
            txt = bc3.find('div', class_='info').find('strong').next_sibling.strip()
            mo = re.search("[\w]{2,8}\s+[0-9]{1,2}, [0-9]{4}", txt)
            return datetime.datetime.strptime(mo.group(0), "%b %d, %Y")

        def get_author(bc3):
            return bc3.find('a', class_='editorlink').get_text().strip()

        def get_duration(bc3):
            txt = bc3.find('span').get_text().strip()
            mo  = re.search("(\d{2}):(\d{2}):(\d{2})", txt)
            return int(mo.group(1)) * 60 * 60 + int(mo.group(2)) * 60 + int(mo.group(3))

        def get_timecodes(bc3):
            for script in bc3.find_all('script'):
                mo = re.search("var\s+TIMES\s?=\s?new\s+Array.?\((\d+(,\d+)+)\)", script.get_text())
                if mo:
                    return [int(tc) for tc in  mo.group(1).split(',')]

        def get_slides(bc3):
            for script in bc3.find_all('script'):
                mo = re.search("var\s+slides\s?=\s?new\s+Array.?\(('.+')\)", script.get_text())
                if mo:
                    return [get_url(slide.replace('\'', '')) for slide in  mo.group(1).split(',')]

        def get_video(bc3):
            for script in bc3.find_all('script'):
                mo = re.search('var jsclassref=\'(.*)\';', script.get_text())
                if mo:
                    b64 = mo.group(1)
                    return "rtmpe://video.infoq.com/cfx/st/%s" % base64.b64decode(b64)

        def add_pdf_if_exist(metadata, bc3):
            # The markup is not the same if authenticated or not
            filename = None
            form = bc3.find('form', id="pdfForm")
            if form:
                metadata['pdf'] = get_url('/pdfdownload.action?filename=') + urllib.quote(form.input['value'], safe='')
            else:
                a = bc3.find('a', class_='link-slides')
                if a:
                    metadata['pdf'] = get_url(a['href'])

        def add_mp3_if_exist(metadata, bc3):
            # The markup is not the same if authenticated or not
            filename = None
            form = bc3.find('form', id="mp3Form")
            if form:
                metadata['mp3'] = get_url('/mp3download.action?filename=') + urllib.quote(form.input['value'], safe='')
            else:
                a = bc3.find('a', class_='link-mp3')
                if a:
                    metadata['mp3'] = get_url(a['href'])

        def add_sections_and_topics(metadata, bc3):
            # Extracting theses two one is quite ugly since there is not clear separation between
            # sections, topics and advertisement. We need to iterate over all children and maintain a
            # state to know who is who
            in_sections = True
            in_topics = False

            sections = []
            topics = []

            for child in bc3.find('dl', class_="tags2").children:
                if not isinstance(child, Tag):
                    continue

                if child.name == 'dt' and "topics" in child['class']:
                    if in_topics:
                        break

                    in_sections = False
                    in_topics = True
                    continue

                if in_sections and child.name == 'dd':
                    sections.append(child.a.get_text().strip());

                if in_topics and child.name == 'dd':
                    topics.append(child.a.get_text().strip());

            metadata['sections'] = sections
            metadata['topics'] = topics

        def add_summary_bio_about(metadata, bc3):
            content = []

            txt = ""
            for child in bc3.find('div', id="summaryComponent"):
                if isinstance(child, NavigableString):
                    txt += unicode(child).strip()
                elif child.name == 'b':
                    content.append(txt)
                    txt = ""
                    continue
                elif child.name == 'br':
                    continue
            content.append(txt)

            metadata['summary'] = content[1]
            metadata['bio']     = content[2]
            metadata['about']   = content[3]

        if not self._metadata:
            box_content_3 = self.soup.find('div', class_='box-content-3')
            metadata = {
                'title': get_title(box_content_3),
                'date' : get_date(box_content_3),
                'auth' : get_author(box_content_3),
                'duration': get_duration(box_content_3),
                'timecodes': get_timecodes(box_content_3),
                'slides': get_slides(box_content_3),
                'video': get_video(box_content_3),
            }
            add_sections_and_topics(metadata, box_content_3)
            add_summary_bio_about(metadata, box_content_3)
            add_mp3_if_exist(metadata, box_content_3)
            add_pdf_if_exist(metadata, box_content_3)

            self._metadata = metadata

        return self._metadata

class RightBarPage(object):
    """A page returned by /rightbar.action

    This page lists all available presentations with pagination.
    """
    def __init__(self, index):
        self.index = index

    def fetch(self, client):
        """Download the page and create the soup"""

        params = {
            "language": "en",
            "selectedTab": "PRESENTATION",
            "startIndex": self.index,
        }
        response = client.open(get_url("/rightbar.action"), urllib.urlencode(params))
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

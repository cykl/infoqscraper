# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2014, Clément MATHIEU
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import base64
import bs4
import datetime
import re

from infoqscraper import client

import six
from six.moves import urllib


def get_summaries(client, filter=None):
    """ Generate presentation summaries in a reverse chronological order.

     A filter class can be supplied to filter summaries or bound the fetching process.
    """
    try:
        index = 0
        while True:
            rb = _RightBarPage(client, index)

            summaries = rb.summaries()
            if filter is not None:
                summaries = filter.filter(summaries)

            for summary in summaries:
                    yield summary

            index += len(summaries)
    except StopIteration:
        pass


class MaxPagesFilter(object):
    """ A summary filter set an upper bound on the number fetched pages"""

    def __init__(self, max_pages):
        self.max_pages = max_pages
        self.page_count = 0

    def filter(self, presentation_summaries):
        if self.page_count >= self.max_pages:
            raise StopIteration

        self.page_count += 1
        return presentation_summaries


class Presentation(object):
    """ An InfoQ presentation.

    """
    def __init__(self, client, id):
        self.client = client
        self.id = id
        self.soup = self._fetch()

    def _fetch(self):
        """Download the page and create the soup"""
        url = client.get_url("/presentations/" + self.id)
        content = self.client.fetch_no_cache(url).decode('utf-8')
        return bs4.BeautifulSoup(content, "html.parser")

    @property
    def metadata(self):
        def get_title(pres_div):
            return pres_div.find('h1', class_="general").div.get_text().strip()

        def get_date(pres_div):
            str = pres_div.find('span', class_='author_general').contents[2]
            str = str.replace('\n',   ' ')
            str = str.replace(six.u('\xa0'), ' ')
            str = str.split("on ")[-1]
            str = str.strip()
            return datetime.datetime.strptime(str, "%b %d, %Y")

        def get_author(pres_div):
            return pres_div.find('span', class_='author_general').contents[1].get_text().strip()

        def get_timecodes(pres_div):
            for script in pres_div.find_all('script'):
                mo = re.search("TIMES\s?=\s?new\s+Array.?\((\d+(,\d+)+)\)", script.get_text())
                if mo:
                    return [int(tc) for tc in mo.group(1).split(',')]

        def get_slides(pres_div):
            for script in pres_div.find_all('script'):
                mo = re.search("var\s+slides\s?=\s?new\s+Array.?\(('.+')\)", script.get_text())
                if mo:
                    return [slide.replace('\'', '') for slide in  mo.group(1).split(',')]

        def get_video(pres_div):
            for script in pres_div.find_all('script'):
                mo = re.search('var jsclassref = \'(.*)\';', script.get_text())
                if mo:
                    b64 = mo.group(1)
                    path = base64.b64decode(b64).decode('utf-8')
                    # Older presentations use flv and the video path does not contain
                    # the extension. Newer presentations use mp4 and include the extension.
                    if path.endswith(".mp4"):
                        return "mp4:%s" % path
                    elif path.endswith(".flv"):
                        return "flv:%s" % path[:-4]
                    else:
                        raise Exception("Unsupported video type: %s" % path)

        def get_bio(div):
            return div.find('p', id="biotext").get_text(strip=True)

        def get_summary(div):
            return "".join(div.find('p', id="summary").get_text("|", strip=True).split("|")[1:])

        def get_about(div):
            return div.find('p', id="conference").get_text(strip=True)

        def add_pdf_if_exist(metadata, pres_div):
            # The markup is not the same if authenticated or not
            form = pres_div.find('form', id="pdfForm")
            if form:
                metadata['pdf'] = client.get_url('/pdfdownload.action?filename=') + urllib.parse.quote(form.input['value'], safe='')
            else:
                a = pres_div.find('a', class_='link-slides')
                if a:
                    metadata['pdf'] = client.get_url(a['href'])

        def add_mp3_if_exist(metadata, bc3):
            # The markup is not the same if authenticated or not
            form = bc3.find('form', id="mp3Form")
            if form:
                metadata['mp3'] = client.get_url('/mp3download.action?filename=') + urllib.parse.quote(form.input['value'], safe='')
            else:
                a = bc3.find('a', class_='link-mp3')
                if a:
                    metadata['mp3'] = client.get_url(a['href'])

        if not hasattr(self, "_metadata"):
            pres_div = self.soup.find('div', class_='presentation_full')
            metadata = {
                'url': client.get_url("/presentations/" + self.id),
                'title': get_title(pres_div),
                'date' : get_date(pres_div),
                'auth' : get_author(pres_div),
                'timecodes': get_timecodes(self.soup),
                'slides': get_slides(self.soup),
                'video_url': six.u("rtmpe://video.infoq.com/cfx/st/"),
                'video_path': get_video(self.soup),
                'bio':        get_bio(pres_div),
                'summary':    get_summary(pres_div),
                'about':      get_about(pres_div),

                }
            add_mp3_if_exist(metadata, pres_div)
            add_pdf_if_exist(metadata, pres_div)

            self._metadata = metadata

        return self._metadata


class _RightBarPage(object):
    """A page returned by /rightbar.action

    This page lists all available presentations with pagination.
    """

    def __init__(self, client, index):
        self.client = client
        self.index = index

    @property
    def soup(self):
        """Download the page and create the soup"""
        try:
            return self._soup
        except AttributeError:
            url = client.get_url("/presentations/%s" % self.index)
            content = self.client.fetch_no_cache(url).decode('utf-8')
            self._soup = bs4.BeautifulSoup(content)

            return self._soup

    def summaries(self):
        """Return a list of all the presentation summaries contained in this page"""
        def create_summary(div):
            def get_id(div):
                return get_url(div).rsplit('/')[-1]

            def get_url(div):
                return client.get_url(div.find('h2', class_='itemtitle').a['href'])

            def get_desc(div):
                return div.p.get_text(strip=True)

            def get_auth(div):
                return div.find('span', class_='author').a['title']

            def get_date(div):
                str = div.find('span', class_='author').get_text()
                str = str.replace('\n',   ' ')
                str = str.replace(six.u('\xa0'), ' ')
                match = re.search(r'on\s+(\w{3} [0-9]{1,2}, 20[0-9]{2})', str)
                return datetime.datetime.strptime(match.group(1), "%b %d, %Y")

            def get_title(div):
                return div.find('h2', class_='itemtitle').a['title']

            return {
                'id':    get_id(div),
                'url':   get_url(div),
                'desc':  get_desc(div),
                'auth':  get_auth(div),
                'date':  get_date(div),
                'title': get_title(div),
            }

        videos = self.soup.findAll('div', {'class': 'news_type_video'})
        return [create_summary(div) for div in videos]

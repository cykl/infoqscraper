# -*- coding: UTF-8 -*-
"""InfoQ web client


Visit http;//www.infoq.com

"""
import base64
import subprocess
import tempfile
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

def fetch(client, url, dir_path):
    response = client.open(url)
    if response.getcode() != 200:
        raise Exception("Fetch failed")

    filename =  url.rsplit('/', 1)[1]
    filename = os.path.join(dir_path, filename)
    with open(filename, "w") as f:
        f.write(response.read())

    return filename

def fetch_all(client, urls, dir_path):
    '''Download all the URLs in the specified directory.'''
    # TODO: Implement parallel download
    filenames = []

    try:
        for url in urls:
            filenames.append(fetch(client, url, dir_path))
    except Exception as e:
        for filename in filenames:
            os.remove(filename)
        raise e

    return filenames

class InfoQ(object):
    """ InfoQ web client entry point"""
    def __init__(self):
        self.authenticated = False
        # InfoQ requires cookies to be logged in. Use a dedicated urllib opener
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieJar()))

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
        response = self.opener.open(url, urllib.urlencode(params))
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
                rb.fetch(self.opener)
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

    def __init__(self, id, opener=urllib2.build_opener()):
        self.id = id
        self.opener = opener

    def fetch(self):
        """Download the page and create the soup"""
        url = get_url("/presentations/" + self.id)
        response = self.opener.open(url)
        if response.getcode() != 200:
            raise Exception("Fetching presentation %s failed" % url)
        return BeautifulSoup(response.read(), "html5lib")


    @property
    def soup(self):
        if not hasattr(self, "_soup"):
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

        if not hasattr(self, "_metadata"):
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




class OfflinePresentation(object):

    def __init__(self, client, presentation):
        self.client = client
        self.presentation = presentation

    @property
    def tmp_dir(self):
        if not hasattr(self, "_tmp_dir"):
            self._tmp_dir = tempfile.mkdtemp(prefix="infoq")

        return self._tmp_dir

    @property
    def audio_path(self):
        return os.path.join(self.tmp_dir, "audio.ogg")

    @property
    def video_path(self):
        return os.path.join(self.tmp_dir, 'video.avi')

    def create_presentation(self, output=None):
        if self.client.authenticated:
            audio = self.download_mp3()
        else:
            video = self.download_video()
            audio = self._extractAudio(video)

        swf_slides = self.download_slides()
        png_slides = self.convert_slides(swf_slides)
        frame_pattern = self.prepare_frames(png_slides)
        output = self.assemble(audio, frame_pattern, output)
        return output

    def assemble(self, audio, frame_pattern, output=None):
        if not output:
            output = os.path.join(self.tmp_dir, "output.avi")
        cmd = ["ffmpeg", "-f", "image2", "-r", "1", "-i", frame_pattern, "-i", audio, output]
        ret = subprocess.call(cmd, stdout=None, stderr=None)
        assert ret == 0
        return output

    def download_video(self):
        video_url =  self.presentation.metadata['video']
        video_name = video_url.rsplit('/', 2)[1]
        video_path = self.video_path

        cmd = ["rtmpdump", '-r', video_url, "-o", video_path]
        ret = subprocess.call(cmd, stdout=None, stderr = None)
        assert ret == 0, cmd
        return video_path

    def download_slides(self):
        return fetch_all(self.client.client, self.presentation.metadata['slides'], self.tmp_dir)

    def download_mp3(self):
        return fetch(self.client.client, self.presentaion.metadata['mp3'], self.tmp_dir)

    def _extractAudio(self, video_path):
        cmd = ["ffmpeg", '-i', video_path, '-vn', '-acodec', 'libvorbis', self.audio_path]
        ret = subprocess.call(cmd , stdout=None, stderr=None)
        assert ret == 0
        return self.audio_path

    def convert_slides(self, swf_slides):
        swf_render = SwfConverter()
        return [swf_render.to_png(s) for s in swf_slides]

    def prepare_frames(self, slides):
        timecodes = self.presentation.metadata['timecodes']

        frame = 0
        for slide_index in xrange(len(slides)):
            for remaining  in xrange(timecodes[slide_index], timecodes[slide_index+1]):
                os.link(slides[slide_index], os.path.join(self.tmp_dir, "frame-{0:04d}.png").format(frame))
                frame += 1

        return os.path.join(self.tmp_dir, "frame-%04d.png")


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


import Image

class SwfConverter(object):
    """Convert SWF slides into an images

    Require swfrender (from swftools: http://www.swftools.org/)
    """

    # Currently rely on swftools
    #
    # Would be great to have a native python dependency to convert swf into png or jpg.
    # However it seems that pyswf  isn't flawless. Some graphical elements (like the text!) are lost during
    # the export.

    def __init__(self, swfrender_path='swfrender'):
        self.swfrender = swfrender_path
        self._stdout = None
        self._stderr = None

    def to_png(self, swf_path, png_path=None):
        """ Convert a slide into a PNG image.

        OSError is raised if swfrender is not available.
        An exception is raised if image cannot be created.
        """
        if not png_path:
            png_path = swf_path.replace(".swf", ".png")

        cmd = [self.swfrender, swf_path, '-o', png_path]
        ret = subprocess.call(cmd, stdout=self._stdout, stderr=self._stderr)
        if ret != 0:
            raise Exception('Failed to convert SWF')
        return png_path

    def to_jpeg(self, swf_path, jpg_path):
        """ Convert a slide into a PNG image.

        OSError is raised if swfrender is not available.
        An exception is raised if image cannot be created.
        """
        png_path = tempfile.mktemp(suffix=".png")
        self.to_png(swf_path, png_path)
        Image.open(png_path).convert('RGB').save(jpg_path, 'jpeg')
        os.remove(png_path)
        return jpg_path


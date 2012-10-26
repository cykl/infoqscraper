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
import errno

# Number of presentation entries per page returned by rightbar.action
RIGHT_BAR_ENTRIES_PER_PAGES = 8

HOME = os.path.expanduser("~")
XDG_CACHE_HOME = os.environ.get("XDG_CACHE_HOME", os.path.join(HOME, ".cache"))
# infoqmedia cache dir
CACHE_DIR = os.path.join(XDG_CACHE_HOME, "infoqmedia")

class DownloadFailedException(Exception):
    pass

class AuthenticationFailedException(Exception):
    pass

class CacheError(Exception):
    pass

def get_url(path, scheme="http"):
    """ Return the full InfoQ URL """
    return scheme + "://www.infoq.com" + path

def _cache_get_path(resource_url):
    return os.path.join(CACHE_DIR, "resources", resource_url)

def cache_get_content(resource_url):
    """Returns the content of a cached resource.

    Args:
        resource_url: The url of the resource

    Returns:
        The content of the resource or None if not in the cache
    """
    cache_path = _cache_get_path(resource_url)
    try:
        with open(cache_path, 'rb') as f:
            return f.read()
    except IOError:
        return None

def cache_get_file(resource_url):
    """Returns the path of a cached resource.

    Args:
        resource_url: The url of the resource

    Returns:
        The file of the resource or None if not in the cache
    """
    cache_path = _cache_get_path(resource_url)
    if os.path.exists(cache_path):
        return cache_path

    return None

def cache_put_content(resource_url, content):
    """Puts the content of a resource into the disk cache.

    Args:
        resource_url: The url of the resource
        content: The content of the resource

    Raises:
        CacheError: If the content cannot be put in cache
    """
    cache_path = _cache_get_path(resource_url)
    # Ensure that cache directories exist
    try:
        dir = os.path.dirname(cache_path)
        os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise CacheError('Failed to create cache directories for ' % cache_path)

    try:
        with open(cache_path, 'wb') as f:
            f.write(content)
    except IOEerror as e:
        raise CacheError('Failed to write in %s' % cache_path)

def cache_put_file(resource_url, file_path):
    """Puts an already downloaded resource into the disk cache.

    Args:
        resource_url: The original url of the resource
        file_path: The resource already available on disk

    Raises:
        CacheError: If the file cannot be put in cache
    """
    cache_path = _cache_get_path(resource_url)

    # Ensure that cache directories exist
    try:
        dir = os.path.dirname(cache_path)
        os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise CacheError('Failed to create cache directories for ' % cache_path)

    try:
        # First try hard link to avoid wasting disk space & overhead
        os.link(file_path, cache_path)
    except OSError:
        try:
            # Use file copy as fallaback
            shutil.copyfile(file_path, cache_path)
        except IOError:
            raise CacheError('Failed to save %s as %s' % (file_path, cache_path))


class InfoQ(object):
    """ InfoQ web client entry point

    Attributes:
        authenticated       If logged in or not
        cache_enabled       If remote resources must be cached on disk or not
    """

    def __init__(self, cache_enabled=False):
        self.authenticated = False
        # InfoQ requires cookies to be logged in. Use a dedicated urllib opener
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieJar()))
        self.cache_enabled = cache_enabled

    def login(self, username, password):
        """ Log in.

        AuthenticationFailedException exception is raised if authentication fails.
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
            raise AuthenticationFailedException("Login failed")

        self.authenticated = True

    def presentation_summaries(self, filter=None):
        """ Generate presentation summaries in a reverse chronological order.

         A filter class can be supplied to filter summaries or bound the fetching process.
        """
        try:
            for page_index in xrange(1000):
                rb = RightBarPage(page_index, self)
                for summary in rb.summaries():
                    if not filter or filter.filter(summary):
                        yield summary
        except StopIteration:
            pass

    def fetch(self, url):
        content = None
        if self.cache_enabled:
            content = cache_get_content(url)
            if not content:
                content = self.fetch_no_cache(url)
            cache_put_content(url, content)
            return content
        else:
            return self.fetch_no_cache(url)

    def fetch_no_cache(self, url):
        """ Fetch the resource specified and return its content.

            DownloadFailedException is raised if the resource cannot be fetched.
        """
        try:
            response = self.opener.open(url)
            return response.read()
        except urllib2.URLError as e:
            raise DownloadFailedException("Failed to get %s.: %s" % (url, e))

    def download(self, url, dir_path):
        content = self.fetch(url)

        filename =  url.rsplit('/', 1)[1]
        filename = os.path.join(dir_path, filename)
        with open(filename, "w") as f:
            f.write(content)

        return filename

    def download_all(self, urls, dir_path):
        """ Download all the resources specified by urls into dir_path. The resulting
            file paths is returned.

            DownloadFailedException is raised if at least one of the resources cannot be downloaded.
            In the case already downloaded resources are erased.
        """

        # TODO: Implement parallel download
        filenames = []

        try:
            for url in urls:
                filenames.append(self.download(url, dir_path))
        except DownloadFailedException as e:
            for filename in filenames:
                os.remove(filename)
            raise e

        return filenames


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
    """ An InfoQ presentation.

    """
    def __init__(self, id, iq):
        self.id = id
        self.iq = iq
        self.soup = self._fetch()

    def _fetch(self):
        """Download the page and create the soup"""
        url = get_url("/presentations/" + self.id)
        content = self.iq.fetch(url)
        return BeautifulSoup(content, "html5lib")

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

    def __init__(self, presentation, ffmpeg="ffmpeg", rtmpdump="rtmpdump", swfrender="swfrender"):
        self.presentation = presentation
        self.ffmpeg = ffmpeg
        self.rtmpdump = rtmpdump
        self.swfrender = swfrender

    @property
    def tmp_dir(self):
        if not hasattr(self, "_tmp_dir"):
            self._tmp_dir = tempfile.mkdtemp(prefix="infoq")

        return self._tmp_dir

    @property
    def _audio_path(self):
        return os.path.join(self.tmp_dir, "audio.ogg")

    @property
    def _video_path(self):
        return os.path.join(self.tmp_dir, 'video.avi')

    def create_presentation(self, output_path):
        ''' Create the presentation.

        The audio track is mixed with the slides. The resulting file is saved as output_path

        DownloadFailedException is raised if some resources cannot be fetched.
        '''
        try:
            audio = self.download_mp3()
        except DownloadFailedException:
            video = self.download_video()
            audio = self._extractAudio(video)

        swf_slides = self.download_slides()

        # Convert slides into PNG since ffmpeg does not support SWF
        png_slides = self._convert_slides(swf_slides)
        # Create one frame per second using the timecode information
        frame_pattern = self._prepare_frames(png_slides)
        # Now Build the video file
        output = self._assemble(audio, frame_pattern, output_path)

        return output


    def download_video(self, output_path=None):
        """Downloads the video.

        If self.iq.cache_enabled is True, then the disk cache is used.

        Args:
            output_path: Where to save the video if not already cached. A
                         file in temporary directory is used if None.

        Returns:
            The path where the video has been saved. Please note that it can not be equals
            to output_path if the video is in cache

        Raises:
            DownloadFailedException: If the video cannot be downloaded.
        """
        video_url =  self.presentation.metadata['video']

        if self.presentation.iq.cache_enabled:
            video_path = cache_get_file(video_url)
            if not video_path:
                video_path = self.download_video_no_cache(output_path=output_path)
            cache_put_file(video_url, video_path)
        else:
            video_path = self.download_video_no_cache(output_path=output_path)

        return video_path

    def download_video_no_cache(self, output_path=None):
        """Downloads the video.

        Args:
            output_path: Where to save the video. A file in temporary directory is
                         used if None.

        Returns:
            The path where the video has been saved.

        Raises:
            DownloadFailedException: If the video cannot be downloaded.
        """
        video_url =  self.presentation.metadata['video']

        if not output_path:
            video_name = video_url.rsplit('/', 2)[1]
            output_path = self._video_path

        try:
            cmd = [self.rtmpdump, '-q', '-r', video_url, "-o", output_path]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            try:
                os.unlink(output_path)
            except OSError:
                pass
            raise DownloadFailedException("Failed to download video at %s: rtmpdump exited with %s" % (video_url, e.returncode))

        return output_path

    def download_slides(self, output_dir=None):
        ''' Download all SWF slides.

        If output_dir is specified slides are downloaded at this location. Otherwise the
        tmp_dir is used. The location of the slides files are returned.

        A DownloadFailedException is raised if at least one of the slides cannot be download..
        '''
        if not output_dir:
            output_dir = self.tmp_dir

        return self.presentation.iq.download_all(self.presentation.metadata['slides'], self.tmp_dir)

    def download_mp3(self, output_path=None):
        ''' Download the audio track.

        If output_path is specified the audio track is downloaded at this location. Otherwise
        the tmp_dir is used. The location of the file is returned.

        A DownloadFailedException is raised if the file cannot be downloaded.
        '''
        if not output_path:
            output_path = self._audio_path

        return self.presentation.iq.download(self.presentation.metadata['mp3'], self.tmp_dir)

    def _assemble(self, audio, frame_pattern, output=None):
        if not output:
            output = os.path.join(self.tmp_dir, "output.avi")
        cmd = [self.ffmpeg, "-f", "image2", "-r", "1", "-i", frame_pattern, "-i", audio, output]
        ret = subprocess.call(cmd, stdout=None, stderr=None)
        assert ret == 0
        return output

    def _extractAudio(self, video_path):
        output_path = self._audio_path
        cmd = [self.ffmpeg, '-i', video_path, '-vn', '-acodec', 'libvorbis', output_path]
        ret = subprocess.call(cmd , stdout=None, stderr=None)
        assert ret == 0
        return output_path

    def _convert_slides(self, swf_slides):
        swf_render = SwfConverter(swfrender=self.swfrender)
        return [swf_render.to_png(s) for s in swf_slides]

    def _prepare_frames(self, slides):
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
    def __init__(self, index, iq):
        self.index = index
        self.iq = iq

    @property
    def soup(self):
        """Download the page and create the soup"""
        try:
            return self._soup
        except AttributeError:
            params = {
                "language": "en",
                "selectedTab": "PRESENTATION",
                "startIndex": self.index,
            }
            # Do not use iq.fetch to avoid caching since the rightbar is a dynamic page
            response = self.iq.opener.open(get_url("/rightbar.action"), urllib.urlencode(params))
            if response.getcode() != 200:
                raise Exception("Fetching rightbar index %s failed" % self.index)
            content = response.read()

            self._soup = BeautifulSoup(content)
            return self._soup

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

        try:
            cmd = [self.swfrender, swf_path, '-o', png_path]
            subprocess.check_output(cmd)
        except subprocess.CalledProcessError as e:
            raise Exception('Failed to convert SWF. swfrender exited with status %s. standard and error output follows:\n%s' % (e.returncode, e.output))

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


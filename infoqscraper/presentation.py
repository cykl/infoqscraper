# -*- coding: utf-8 -*-
#
# Copyright (c) 2012, Clément MATHIEU
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
import contextlib
import datetime
import errno
from infoqscraper import client
from infoqscraper import utils
import os
import re
import shutil
import subprocess
import tempfile
import urllib

def get_summaries(client, filter=None):
    """ Generate presentation summaries in a reverse chronological order.

     A filter class can be supplied to filter summaries or bound the fetching process.
    """
    try:
        for page_index in xrange(1000):
            rb = _RightBarPage(client, page_index)
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
        if self.seen / _RightBarPage.ENTRIES_PER_PAGES >= self.max_pages:
            raise StopIteration

        self.seen += 1
        return presentation_summary


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
            str = str.replace(u'\n',   u' ')
            str = str.replace(u'\xa0', u' ')
            str = str.split("on ")[-1]
            str = str.strip()
            return datetime.datetime.strptime(str, "%b %d, %Y")

        def get_author(pres_div):
            return pres_div.find('span', class_='author_general').contents[1].get_text().strip()

        def get_timecodes(pres_div):
            for script in pres_div.find_all('script'):
                mo = re.search("var\s+TIMES\s?=\s?new\s+Array.?\((\d+(,\d+)+)\)", script.get_text())
                if mo:
                    return [int(tc) for tc in  mo.group(1).split(',')]

        def get_slides(pres_div):
            for script in pres_div.find_all('script'):
                mo = re.search("var\s+slides\s?=\s?new\s+Array.?\(('.+')\)", script.get_text())
                if mo:
                    return [client.get_url(slide.replace('\'', '')) for slide in  mo.group(1).split(',')]

        def get_video(pres_div):
            for script in pres_div.find_all('script'):
                mo = re.search('var jsclassref = \'(.*)\';', script.get_text())
                if mo:
                    b64 = mo.group(1)
                    path = base64.b64decode(b64)
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
                metadata['pdf'] = client.get_url('/pdfdownload.action?filename=') + urllib.quote(form.input['value'], safe='')
            else:
                a = pres_div.find('a', class_='link-slides')
                if a:
                    metadata['pdf'] = client.get_url(a['href'])

        def add_mp3_if_exist(metadata, bc3):
            # The markup is not the same if authenticated or not
            form = bc3.find('form', id="mp3Form")
            if form:
                metadata['mp3'] = client.get_url('/mp3download.action?filename=') + urllib.quote(form.input['value'], safe='')
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
                'video_url': "rtmpe://video.infoq.com/cfx/st/",
                'video_path': get_video(self.soup),
                'bio':        get_bio(pres_div),
                'summary':    get_summary(pres_div),
                'about':      get_about(pres_div),

                }
            add_mp3_if_exist(metadata, pres_div)
            add_pdf_if_exist(metadata, pres_div)

            self._metadata = metadata

        return self._metadata

class Downloader(object):

    def __init__(self, presentation, ffmpeg="ffmpeg", rtmpdump="rtmpdump", swfrender="swfrender"):
        self.presentation = presentation
        self.ffmpeg = ffmpeg
        self.rtmpdump = rtmpdump
        self.swfrender = swfrender

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self.tmp_dir)

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

    def create_presentation(self, output_path=None):
        """ Create the presentation.

        The audio track is mixed with the slides. The resulting file is saved as output_path

        DownloadFailedException is raised if some resources cannot be fetched.
        """
        try:
            audio = self.download_mp3()
        except client.DownloadError:
            audio = self.download_video()

        raw_slides = self.download_slides()

        # Convert slides into JPG since ffmpeg does not support SWF
        jpg_slides = self._convert_slides(raw_slides)
        # Create one frame per second using the timecode information
        frame_pattern = self._prepare_frames(jpg_slides)
        # Now Build the video file
        output = self._assemble(audio, frame_pattern, output=output_path)

        return output

    def download_video(self, output_path=None):
        """Downloads the video.

        If self.client.cache_enabled is True, then the disk cache is used.

        Args:
            output_path: Where to save the video if not already cached. A
                         file in temporary directory is used if None.

        Returns:
            The path where the video has been saved. Please note that it can not be equals
            to output_path if the video is in cache

        Raises:
            DownloadFailedException: If the video cannot be downloaded.
        """
        rvideo_path =  self.presentation.metadata['video_path']

        if self.presentation.client.cache:
            video_path = self.presentation.client.cache.get_path(rvideo_path)
            if not video_path:
                video_path = self.download_video_no_cache(output_path=output_path)
                self.presentation.client.cache.put_path(rvideo_path, video_path)
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
        video_url  = self.presentation.metadata['video_url']
        video_path = self.presentation.metadata['video_path']

        if not output_path:
            output_path = self._video_path

        try:
            cmd = [self.rtmpdump, '-q', '-r', video_url, '-y', video_path, "-o", output_path]
            utils.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            try:
                os.unlink(output_path)
            except OSError:
                pass
            raise client.DownloadError("Failed to download video at %s: rtmpdump exited with %s" % (video_url, e.returncode))

        return output_path

    def download_slides(self, output_dir=None):
        """ Download all SWF slides.

        If output_dir is specified slides are downloaded at this location. Otherwise the
        tmp_dir is used. The location of the slides files are returned.

        A DownloadFailedException is raised if at least one of the slides cannot be download..
        """
        if not output_dir:
            output_dir = self.tmp_dir

        return self.presentation.client.download_all(self.presentation.metadata['slides'], output_dir)

    def download_mp3(self, output_path=None):
        """ Download the audio track.

        If output_path is specified the audio track is downloaded at this location. Otherwise
        the tmp_dir is used. The location of the file is returned.

        A DownloadFailedException is raised if the file cannot be downloaded.
        """
        if not output_path:
            output_path = self._audio_path

        dir = os.path.dirname(output_path)
        filename = os.path.basename(output_path)

        return self.presentation.client.download(self.presentation.metadata['mp3'], dir, filename=filename)

    def _assemble(self, audio, frame_pattern, output=None):
        if not output:
            output = os.path.join(self.tmp_dir, "output.avi")

        try:
            # Try to be compatible as much as possible with old ffmpeg releases (>= 0.7)
            #   - Do not use new syntax options
            #   - Do not use libx264, not available on old Ubuntu/Debian
            #   - Do not use -threads auto, not available on 0.8.*
            #   - Old releases are very picky regarding arguments position
            #
            # 0.5 (Debian Squeeze & Ubuntu 10.4) is not supported because of
            # scaling issues with image2.
            cmd = [
                    self.ffmpeg, "-v", "0",
                    "-i", audio, 
                    "-f", "image2", "-r", "1", "-s", "hd720","-i", frame_pattern,
                    "-map", "1:0", "-acodec", "libmp3lame", "-ab", "128k",
                    "-map", "0:1", "-vcodec", "mpeg4", "-vb", "2M",
                    output
                ]
            utils.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise Exception("Failed to create final movie as %s.\n"
                            "\tExit code: %s\n"
                            "\tOutput:\n%s"
                            % (output, e.returncode, e.output))
        return output

    def _convert_slides(self, slides):
        swf_render = utils.SwfConverter(swfrender_path=self.swfrender)

        def convert(slide):
            if slide.endswith("swf"):
                return swf_render.to_jpeg(slide)
            elif slide.endswith("jpg"):
                return slide
            else:
                raise Exception("Unsupported slide type: %s" % slide)

        return [convert(s) for s in slides]

    def _prepare_frames(self, slides, ext="jpg"):
        timecodes = self.presentation.metadata['timecodes']

        frame = 0
        for slide_index in xrange(len(slides)):
            src = slides[slide_index]
            for remaining  in xrange(timecodes[slide_index], timecodes[slide_index+1]):
                dst = os.path.join(self.tmp_dir, "frame-{0:04d}." + ext).format(frame)
                try:
                    os.link(src, dst)
                except OSError as e:
                    if e.errno == errno.EMLINK:
                        # Create a new reference file when the upper limit is reached
                        # (previous to Linux 3.7, btrfs had a very low limit)
                        shutil.copyfile(src, dst)
                        src = dst
                    else:
                        raise e
                    
                frame += 1

        return os.path.join(self.tmp_dir, "frame-%04d." +  ext)


class _RightBarPage(object):
    """A page returned by /rightbar.action

    This page lists all available presentations with pagination.
    """

    # Number of presentation entries per page returned by rightbar.action
    ENTRIES_PER_PAGES = 10

    def __init__(self, client, index):
        self.client = client
        self.index = index

    @property
    def soup(self):
        """Download the page and create the soup"""
        try:
            return self._soup
        except AttributeError:
            url = client.get_url("/presentations/%s" % (self.index * _RightBarPage.ENTRIES_PER_PAGES))
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
                str = str.replace(u'\n',   u' ')
                str = str.replace(u'\xa0', u' ')
                str = str.split("on ")[-1]
                str = str.strip()
                return datetime.datetime.strptime(str, "%b %d, %Y")

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

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
import datetime
import errno
from infoqscraper import client
from infoqscraper import utils
import os
import re
import shutil
import subprocess
import tempfile

import six
from six.moves import http_cookiejar
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
                    return [client.get_url(slide.replace('\'', '')) for slide in  mo.group(1).split(',')]

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


class Downloader(object):

    def __init__(self, presentation, output, **kwargs):
        self.presentation = presentation
        self.output = output

        self.ffmpeg = kwargs['ffmpeg']
        self.rtmpdump = kwargs['rtmpdump']
        self.swfrender = kwargs['swfrender']
        self.overwrite = kwargs['overwrite']
        self.type = kwargs['type']

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

    def create_presentation(self):
        """ Create the presentation.

        The audio track is mixed with the slides. The resulting file is saved as self.output

        DownloadFailedException is raised if some resources cannot be fetched.
        """
        # Avoid wasting time and bandwidth if we known that conversion will fail.
        if not self.overwrite and os.path.exists(self.output):
            raise Exception("File %s already exist and --overwrite not specified" % self.output)

        video = self.download_video()
        raw_slides = self.download_slides()

        # ffmpeg does not support SWF
        png_slides = self._convert_slides(raw_slides)
        # Create one frame per second using the time code information
        frame_pattern = self._prepare_frames(png_slides)

        return self._assemble(video, frame_pattern)

    def download_video(self):
        """Downloads the video.

        If self.client.cache_enabled is True, then the disk cache is used.

        Returns:
            The path where the video has been saved.

        Raises:
            DownloadFailedException: If the video cannot be downloaded.
        """
        rvideo_path = self.presentation.metadata['video_path']

        if self.presentation.client.cache:
            video_path = self.presentation.client.cache.get_path(rvideo_path)
            if not video_path:
                video_path = self.download_video_no_cache()
                self.presentation.client.cache.put_path(rvideo_path, video_path)
        else:
            video_path = self.download_video_no_cache()

        return video_path

    def download_video_no_cache(self):
        """Downloads the video.

        Returns:
            The path where the video has been saved.

        Raises:
            DownloadFailedException: If the video cannot be downloaded.
        """
        video_url = self.presentation.metadata['video_url']
        video_path = self.presentation.metadata['video_path']

        try:
            cmd = [self.rtmpdump, '-q', '-r', video_url, '-y', video_path, "-o", self._video_path]
            utils.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            try:
                os.unlink(self._video_path)
            except OSError:
                pass
            raise client.DownloadError("Failed to download video at %s: rtmpdump exited with %s.\n\tOutput:\n%s"
                                       % (video_url, e.returncode, e.output))

        return self._video_path

    def download_slides(self):
        """ Download all SWF slides.

        The location of the slides files are returned.

        A DownloadFailedException is raised if at least one of the slides cannot be download..
        """
        return self.presentation.client.download_all(self.presentation.metadata['slides'], self.tmp_dir)

    def _ffmpeg_legacy(self, audio, frame_pattern):
        # Try to be compatible as much as possible with old ffmpeg releases (>= 0.7)
        #   - Do not use new syntax options
        #   - Do not use libx264, not available on old Ubuntu/Debian
        #   - Do not use -threads auto, not available on 0.8.*
        #   - Old releases are very picky regarding arguments position
        #   - -n is not supported on 0.8
        #
        # 0.5 (Debian Squeeze & Ubuntu 10.4) is not supported because of
        # scaling issues with image2.
        cmd = [
            self.ffmpeg, "-v", "0",
            "-i", audio,
            "-f", "image2", "-r", "1", "-s", "hd720", "-i", frame_pattern,
            "-map", "1:0", "-acodec", "libmp3lame", "-ab", "128k",
            "-map", "0:1", "-vcodec", "mpeg4", "-vb", "2M", "-y", self.output
        ]

        if not self.overwrite and os.path.exists(self.output):
            # Handle already existing file manually since nor -n nor -nostdin is available on 0.8
            raise Exception("File %s already exist and --overwrite not specified" % self.output)

        return cmd

    def _ffmpeg_h264(self, audio, frame_pattern):
        return [
            self.ffmpeg, "-v", "error",
            "-i", audio,
            "-r", "1", "-i", frame_pattern,
            "-c:a", "copy",
            "-c:v", "libx264", "-profile:v", "baseline", "-preset", "ultrafast", "-level", "3.0",
            "-crf", "28", "-pix_fmt", "yuv420p",
            "-s", "1280x720",
            "-y" if self.overwrite else "-n",
            self.output
        ]

    def _ffmpeg_h264_overlay(self, audio, frame_pattern):
        return [
            self.ffmpeg, "-v", "error",
            "-i", audio,
            "-f", "image2", "-r", "1", "-s", "hd720", "-i", frame_pattern,
            "-filter_complex",
            "".join([
                "color=size=1280x720:c=Black [base];",
                "[0:v] setpts=PTS-STARTPTS, scale=320x240 [speaker];",
                "[1:v] setpts=PTS-STARTPTS, scale=w=1280-320:h=-1[slides];",
                "[base][slides]  overlay=shortest=1:x=0:y=0 [tmp1];",
                "[tmp1][speaker] overlay=shortest=1:x=main_w-320:y=main_h-240",
                ]),
            "-acodec", "libmp3lame", "-ab", "92k",
            "-vcodec", "libx264", "-profile:v", "baseline", "-preset", "fast", "-level", "3.0", "-crf", "28",
            "-y" if self.overwrite else "-n",
            self.output
        ]

    def _assemble(self, audio, frame_pattern):
        if self.type == "legacy":
            cmd = self._ffmpeg_legacy(audio, frame_pattern)
        elif self.type == "h264":
            cmd = self._ffmpeg_h264(audio, frame_pattern)
        elif self.type == "h264_overlay":
            cmd = self._ffmpeg_h264_overlay(audio, frame_pattern)
        else:
            raise Exception("Unknown output type %s" % self.type)

        try:
            utils.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise Exception("Failed to create final movie as %s.\n"
                            "\tExit code: %s\n"
                            "\tOutput:\n%s"
                            % (self.output, e.returncode, e.output))

    def _convert_slides(self, slides):
        swf_render = utils.SwfConverter(swfrender_path=self.swfrender)

        def convert(slide):
            if slide.endswith("swf"):
                return swf_render.to_png(slide)
            elif slide.endswith("jpg"):
                return slide
            else:
                raise Exception("Unsupported slide type: %s" % slide)

        return [convert(s) for s in slides]

    def _prepare_frames(self, slides):
        timecodes = self.presentation.metadata['timecodes']
        ext = os.path.splitext(slides[0])[1]

        frame = 0
        for slide_index, src in enumerate(slides):
            for remaining in range(timecodes[slide_index], timecodes[slide_index+1]):
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

        return os.path.join(self.tmp_dir, "frame-%04d." + ext)


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

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
        if self.seen / _RightBarPage.RIGHT_BAR_ENTRIES_PER_PAGES >= self.max_pages:
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
        content = self.client.fetch(url).decode('utf-8')
        return bs4.BeautifulSoup(content, "html5lib")

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
                    return [client.get_url(slide.replace('\'', '')) for slide in  mo.group(1).split(',')]

        def get_video(bc3):
            for script in bc3.find_all('script'):
                mo = re.search('var jsclassref=\'(.*)\';', script.get_text())
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


        def add_pdf_if_exist(metadata, bc3):
            # The markup is not the same if authenticated or not
            form = bc3.find('form', id="pdfForm")
            if form:
                metadata['pdf'] = client.get_url('/pdfdownload.action?filename=') + urllib.quote(form.input['value'], safe='')
            else:
                a = bc3.find('a', class_='link-slides')
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

        def add_sections_and_topics(metadata, bc3):
            # Extracting theses two one is quite ugly since there is not clear separation between
            # sections, topics and advertisement. We need to iterate over all children and maintain a
            # state to know who is who
            in_sections = True
            in_topics = False

            sections = []
            topics = []

            for child in bc3.find('dl', class_="tags2").children:
                if not isinstance(child, bs4.element.Tag):
                    continue

                if child.name == 'dt' and "topics" in child['class']:
                    if in_topics:
                        break

                    in_sections = False
                    in_topics = True
                    continue

                if in_sections and child.name == 'dd':
                    sections.append(child.a.get_text().strip())

                if in_topics and child.name == 'dd':
                    topics.append(child.a.get_text().strip())

            metadata['sections'] = sections
            metadata['topics'] = topics

        def add_summary_bio_about(metadata, bc3):
            content = []

            txt = ""
            for child in bc3.find('div', id="summaryComponent"):
                if isinstance(child, bs4.element.NavigableString):
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
                'url': client.get_url("/presentations/" + self.id),
                'title': get_title(box_content_3),
                'date' : get_date(box_content_3),
                'auth' : get_author(box_content_3),
                'duration': get_duration(box_content_3),
                'timecodes': get_timecodes(box_content_3),
                'slides': get_slides(box_content_3),
                'video_url': "rtmpe://video.infoq.com/cfx/st/",
                'video_path': get_video(box_content_3),
                }
            add_sections_and_topics(metadata, box_content_3)
            add_summary_bio_about(metadata, box_content_3)
            add_mp3_if_exist(metadata, box_content_3)
            add_pdf_if_exist(metadata, box_content_3)

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
            video = self.download_video()
            audio = self._extractAudio(video)

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
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
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
            cmd = [self.ffmpeg, "-v", "error", "-f", "image2", "-r", "1", "-i", frame_pattern, "-i", audio, output]
            ret = subprocess.call(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise Exception("Failed to create final movie as %s.\n"
                            "\tExit code: %s\n"
                            "\tOutput:\n%s"
                            % (output, e.returncode, e.output))
        return output

    def _extractAudio(self, video_path):
        output_path = self._audio_path
        try:
            cmd = [self.ffmpeg, "-v", "error", '-i', video_path, '-vn', '-acodec', 'libvorbis', output_path]
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise Exception("Failed to extract audio track from %s to %s.\n"
                            "\tExit code: %s\n"
                            "\tOutput:\n%s"
                            % (video_path, output_path, e.returncode, e.output))
        return output_path

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
            for remaining  in xrange(timecodes[slide_index], timecodes[slide_index+1]):
                os.link(slides[slide_index], os.path.join(self.tmp_dir, "frame-{0:04d}." + ext).format(frame))
                frame += 1

        return os.path.join(self.tmp_dir, "frame-%04d." +  ext)


class _RightBarPage(object):
    """A page returned by /rightbar.action

    This page lists all available presentations with pagination.
    """

    # Number of presentation entries per page returned by rightbar.action
    RIGHT_BAR_ENTRIES_PER_PAGES = 8


    def __init__(self, client, index):
        self.client = client
        self.index = index

    @property
    def soup(self):
        """Download the page and create the soup"""
        try:
            return self._soup
        except AttributeError:
            params = {
                "language": "en",
                "selectedTab": "PRESENTATION",
                "startIndex": self.index * _RightBarPage.RIGHT_BAR_ENTRIES_PER_PAGES,
                }
            # Do not use iq.fetch to avoid caching since the rightbar is a dynamic page
            url = client.get_url("/rightbar.action")
            with contextlib.closing(self.client.opener.open(url, urllib.urlencode(params))) as response:
                if response.getcode() != 200:
                    raise Exception("Fetching rightbar index %s failed" % self.index)
                content = response.read().decode('utf-8')

                self._soup = bs4.BeautifulSoup(content)

            return self._soup

    def summaries(self):
        """Return a list of all the presentation summaries contained in this page"""
        def create_summary(div):
            def get_id(div):
                return get_path(div).rsplit('/', 1)[1]

            def get_path(div):
                # remove session id if present
                return div.find('a')['href'].rsplit(';', 2)[0]

            def get_url(div):
                return client.get_url(get_path(div))

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
                'url' :  get_url(div),
                'desc' : get_desc(div),
                'auth' : get_auth(div),
                'date' : get_date(div),
                'title': get_title(div),
                }

        entries = self.soup.findAll('div', {'class': 'entry'})
        return [create_summary(div) for div in entries]

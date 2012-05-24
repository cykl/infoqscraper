#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
infoqmedia.py
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


from PIL import Image
import os
import re
import shutil
import subprocess
import tempfile
import threading
import urllib2
import argparse
import sys

__author__ = 'mathieuc'

class InfoQException(Exception):
    pass

class _SlideFetcherThread(threading.Thread):
    def __init__(self, jpgSlidesPath, dumper, tmpDir):
        threading.Thread.__init__(self)
        self.dumper = dumper
        self.tmpDir = tmpDir
        self.jpgSlidesPath = jpgSlidesPath

    def run(self):
        for slideIndex in xrange(len(self.dumper.slides)):
            swfSlidePath = self.dumper._downloadSlide(self.tmpDir, slideIndex)
            self.jpgSlidesPath.append(self.dumper._convertSlideToJpeg(swfSlidePath))
            self.dumper._earlyUnlink(swfSlidePath)

class InfoQPresentationDumper:
    _baseUrl = "http://www.infoq.com/presentations/"

    _nameRegexp      = re.compile(r'presentations/infoq-(?P<name>[^.]+)\.mp3')
    _timecodesRegexp = re.compile('var *TIMES *= *new Array\\((?P<list>.+)\\);')
    _slidesRegexp    = re.compile('var slides *= *new Array.(?P<list>.+).;')
    _durationRegexp  = re.compile(r'Duration: (?P<hours>[0-9]{2}):(?P<minutes>[0-9]{2}):(?P<seconds>[0-9]{2}).(?P<centiseconds>[0-9]{2})')

    def __init__(self, presentation, ffmpeg="ffmpeg", swfrender="swfrender", rtmpdump="rtmpdump", earlyClean=True, quiet=False, verbose=False):
        if presentation.startswith("http://"):
            self.url = url
        else:
            self.url = InfoQPresentationDumper._baseUrl + presentation

        self.ffmpeg    = ffmpeg
        self.swfrender = swfrender
        self.rtmpdump  = rtmpdump

        self.earlyClean = earlyClean
        self.verbose    = verbose
        if quiet:
            self.stdout = open(os.devnull, 'w')
            self.stderr = open(os.devnull, 'w')
        else:
            self.stdout = None
            self.stderr = None

        try:
            self.pageData  = urllib2.urlopen(self.url).read()
            self.name      = self._getName()
            self.timeCodes = self._getTimecodes()
            self.timeCodes[0] = 0
            self.slides    = self._getSlides()
            assert self.name
            assert len(self.timeCodes) == len(self.slides) + 1
            self._log("timecodes: %s" % self.timeCodes)
            self._log("slides: %s" % self.slides)
        except (urllib2.URLError, urllib2.HTTPError) as e:
            raise InfoQException("Failed to retrieve: %s" % self.url)

    def _log(self, msg):
        if self.verbose:
            print msg

    def _getName(self):
        groups = InfoQPresentationDumper._nameRegexp.search(self.pageData)
        assert groups
        return groups.groupdict()['name']

    def _getTimecodes(self):
        groups = InfoQPresentationDumper._timecodesRegexp.search(self.pageData)
        assert groups
        return map(lambda x: int(x), groups.groupdict()['list'].split(','))

    def _getSlides(self):
        groups = InfoQPresentationDumper._slidesRegexp.search(self.pageData)
        assert groups
        return map(lambda x: x.replace('\'', ''), groups.groupdict()['list'].split(','))

    def _downloadVideo(self, tmpDir):
        videoPath = os.path.join(tmpDir, "%s.mp4" % self.name)
        videoUrl = "rtmpe://video.infoq.com/cfx/st/presentations/%s.mp4" % self.name
        self._log("Downloading video from %s" % videoUrl)
        cmd = [self.rtmpdump, '-r', videoUrl, "-o", videoPath]
        ret = subprocess.call(cmd, stdout=self.stdout, stderr = self.stderr)
        assert ret == 0
        return videoPath

    def _extractAudio(self, tmpDir, videoPath):
        audioPath = os.path.join(tmpDir, "%s.mp3" % self.name)
        cmd = [self.ffmpeg, '-i', videoPath, '-ab', '128000', '-ar', '44100', '-vn', '-acodec', 'ac3',  audioPath]
        ret = subprocess.call(cmd , stdout=self.stdout, stderr = self.stderr)
        assert ret == 0
        return audioPath

    def _getDuration(self, mediaPath):
        cmd = [self.ffmpeg, '-i', mediaPath]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        assert p.returncode == 1
        groups = InfoQPresentationDumper._durationRegexp.search(stderr)
        assert groups

        duration = 0
        duration += int(groups.groupdict()['hours']) * 60 * 60
        duration += int(groups.groupdict()['minutes']) * 60
        duration += int(groups.groupdict()['seconds'])
        return duration

    def _downloadSlide(self, tmpDir, slideIndex):
        slidePath = self.slides[slideIndex]
        slideUrl  = "http://www.infoq.com%s" % slidePath

        self._log("Downloading slide %s from %s" % (slideIndex, slideUrl))
        swfPath = os.path.join(tmpDir, "slide-%s.swf" % slideIndex)
        data = urllib2.urlopen(slideUrl).read()
        with open(swfPath, 'w') as f:
            f.write(data)

        return swfPath

    def _convertSlideToJpeg(self, swfSlidePath):
        pngSlidePath = swfSlidePath.replace(".swf", ".png")
        cmd = [self.swfrender, swfSlidePath, '-o', pngSlidePath]
        ret = subprocess.call(cmd, stdout=self.stdout, stderr=self.stderr)
        assert ret == 0

        jpgSlidePath = swfSlidePath.replace(".swf", ".jpg")
        Image.open(pngSlidePath).convert('RGB').save(jpgSlidePath, 'jpeg')
        self._log("Converting slide to JPEG: %s -> %s" % (swfSlidePath, jpgSlidePath))

        os.unlink(pngSlidePath)
        return jpgSlidePath

    def _earlyUnlink(self, path):
        if self.earlyClean:
            os.unlink(path)

    def _createVideo(self, audioPath, slidePattern, outputPath):
        self._log("Creating final video %s" % outputPath)
        cmd = [self.ffmpeg, "-f", "image2", "-r", "1", "-i", slidePattern, "-i", audioPath, outputPath]
        ret = subprocess.call(cmd, stdout=self.stdout, stderr=self.stderr)
        assert ret == 0
        return outputPath

    def save(self, outputPath, tmpDir=None):
        if tmpDir:
            assert os.path.exists(tmpDir) and os.path.isdir(tmpDir)
        else:
            tmpDir = tempfile.mkdtemp()

        try:
            # Fetch slides while downloading the video. Fetching slides can take a significant amount of time
            jpgSlidesPath = []
            t = _SlideFetcherThread(jpgSlidesPath, self, tmpDir)
            t.start()

            videoPath = self._downloadVideo(tmpDir)
            audioPath = self._extractAudio(tmpDir, videoPath)
            duration  = self._getDuration(audioPath)
            self.timeCodes.append(duration)
            self._earlyUnlink(videoPath)

            if t.is_alive:
                self._log("Video downloading finished. Waiting for the slide fetcher")
                t.join()

            frame = 0
            for slideIndex in xrange(len(self.slides)):
                for remaining  in xrange(self.timeCodes[slideIndex], self.timeCodes[slideIndex+1]):
                    os.link(jpgSlidesPath[slideIndex], os.path.join(tmpDir, "frame-{0:04d}.jpg".format(frame)))
                    frame += 1

                self._earlyUnlink(jpgSlidesPath[slideIndex])

            return self._createVideo(audioPath, os.path.join(tmpDir, "frame-%04d.jpg"), outputPath)

        finally:
            shutil.rmtree(tmpDir)



def main():
    class StoreAndCheckBinary(argparse.Action):

        def __call__(self, parser, namespace, values, option_string=None):
            if not os.path.exists(values):
                print >> sys.stderr, "%s binary cannot be found at %s" % (self.dest, values)
                sys.exit(1)

            setattr(namespace, self.dest, values)

    store_check = StoreAndCheckBinary

    parser = argparse.ArgumentParser(description='Download presentations from InfoQ.')
    parser.add_argument('-f', '--ffmpeg'   , nargs="?", type=str, action=store_check, default="ffmpeg",    help='ffmpeg binary')
    parser.add_argument('-s', '--swfrender', nargs="?", type=str, action=store_check, default="swfrender", help='swfrender binary')
    parser.add_argument('-r', '--rtmpdump' , nargs="?", type=str, action=store_check, default="rtmpdump" , help='rtmpdump binary')
    parser.add_argument('-o', '--output'   , nargs="?", type=str, help='output file')
    parser.add_argument('-q', '--quiet'    , action='store_true', help='quiet mode')
    parser.add_argument('-d', '--debug'    , action='store_true', help='debug mode')

    parser.add_argument('name', help='name of the presentation or url')

    args = parser.parse_args()

    if not args.output:
        args.output = "%s.avi" % args.name

    try:
        dumper = InfoQPresentationDumper(args.name,
            ffmpeg=args.ffmpeg,
            swfrender=args.swfrender,
            rtmpdump=args.rtmpdump,
            quiet=args.quiet,
            verbose=args.debug
            )

        path = dumper.save(args.output)
        return 0

    except InfoQException as e:
        print >> sys.stderr, e
        return 1
    except  KeyboardInterrupt:
        print >> sys.stderr, "Aborted."

if __name__ == "__main__":
    sys.exit(main())

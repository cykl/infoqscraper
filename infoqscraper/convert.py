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

import errno
import os
import shutil
import subprocess
import tempfile

from infoqscraper import client
from infoqscraper import ConversionError

from six.moves import http_cookiejar
from six.moves import urllib


class Converter(object):

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

        DownloadError is raised if some resources cannot be fetched.
        ConversionError is raised if the final video cannot be created.
        """
        # Avoid wasting time and bandwidth if we known that conversion will fail.
        if not self.overwrite and os.path.exists(self.output):
            raise ConversionError("File %s already exist and --overwrite not specified" % self.output)

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
            DownloadError: If the video cannot be downloaded.
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
            DownloadError: If the video cannot be downloaded.
        """
        video_url = self.presentation.metadata['video_url']
        video_path = self.presentation.metadata['video_path']

        # After a while, when downloading a long video (> 1h), the RTMP server seems to reset the connection (rtmpdump
        # returns exit code 2). The only way to get the full stream is to resume the download.
        resume_download = True
        while resume_download:
            try:
                cmd = [self.rtmpdump, '-q', '-e', '-r', video_url, '-y', video_path, "-o", self._video_path]
                subprocess.check_output(cmd, stderr=subprocess.STDOUT)
                resume_download = False
            except subprocess.CalledProcessError as e:
                if e.returncode != 2:
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

        A DownloadError is raised if at least one of the slides cannot be download..
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
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            msg = "Failed to create final movie as %s.\n" \
                  "\tCommand: %s\n" \
                  "\tExit code: %s\n" \
                  "\tOutput:\n%s" % (self.output, " ".join(cmd), e.returncode, e.output)

            if self.type != "legacy":
                msg += "\n Please note that %s output format requires a recent version of ffmpeg and libx264." \
                       " Perhaps you should check your setup." \
                       % self.type

            raise ConversionError(msg)

    def _convert_slides(self, slides):

        def convert(slide):
            if slide.endswith("swf"):
                png_slide = slide.replace(".swf", ".png")
                swf2png(slide, png_slide, swfrender_path=self.swfrender)
                return png_slide
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


def swf2png(swf_path, png_path, swfrender_path="swfrender"):
    """Convert SWF slides into a PNG image

    Raises:
        OSError is raised if swfrender is not available.
        ConversionError is raised if image cannot be created.
    """
    # Currently rely on swftools
    #
    # Would be great to have a native python dependency to convert swf into png or jpg.
    # However it seems that pyswf  isn't flawless. Some graphical elements (like the text!) are lost during
    # the export.
    try:
        cmd = [swfrender_path, swf_path, '-o', png_path]
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise ConversionError("Failed to convert SWF file %s.\n"
                              "\tCommand: %s\n"
                              "\tExit status: %s.\n"
                              "\tOutput:\n%s"
                              % (swf_path, " ".join(cmd), e.returncode, e.output))


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
from infoqscraper import client
from infoqscraper import presentation
from infoqscraper import test
from infoqscraper import utils
import os
import shutil
import tempfile
import unittest2
import subprocess


class TestCheckOutputBackport(unittest2.TestCase):

    def test_ok(self):
        utils.check_output(["python", "-h"])

    def test_error(self):
        try:
            with open(os.devnull, "w") as fnull:
                utils.check_output(["python", "--foo"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            self.assertEquals(e.returncode, 2)


class TestSwfConverter(unittest2.TestCase):

    def setUp(self):
        self.iq = client.InfoQ()
        self.tmp_dir = tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    @test.use_cache
    def test_swf(self):
        converter = utils.SwfConverter()

        # Fetch a slide
        pres = presentation.Presentation(self.iq, "Java-GC-Azul-C4")
        swf_path = self.iq.download(pres.metadata['slides'][0], self.tmp_dir)

        # SWF -> PNG
        png_path = swf_path.replace('.swf', '.png')
        converter.to_png(swf_path, png_path)
        stat_info = os.stat(png_path)
        self.assertGreater(stat_info.st_size, 1000)

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
from infoqscraper import test
import os
import shutil
import tempfile
import unittest2

class TestLogin(unittest2.TestCase):
    def setUp(self):
        self.iq = client.InfoQ()

    def test_not_authenticated(self):
        self.assertFalse(self.iq.authenticated)

    def test_login_ok(self):
        if test.USERNAME and test.PASSWORD:
            self.iq.login(test.USERNAME,test. PASSWORD)
            self.assertTrue(self.iq.authenticated)

    def test_login_fail(self):
        self.assertRaises(Exception, self.iq.login, "user", "password")
        self.assertFalse(self.iq.authenticated)


class TestFetch(unittest2.TestCase):

    def setUp(self):
        self.iq = client.InfoQ()

    @test.use_cache
    def test_fetch(self):
        p = test.get_latest_presentation(self.iq)
        content = self.iq.fetch(p.metadata['slides'][0])
        self.assertIsInstance(content, basestring)
        self.assertGreater(len(content), 1000)

    @test.use_cache
    def test_fetch_error(self):
        with self.assertRaises(client.DownloadError):
            self.iq.fetch(client.get_url("/IDONOTEXIST"))

    def test_fetch_wo_cache(self):
        p = test.get_latest_presentation(self.iq)
        content = self.iq.fetch(p.metadata['slides'][0])
        self.assertIsInstance(content, basestring)
        self.assertGreater(len(content), 1000)

    def test_fetch_error_wo_cache(self):
        with self.assertRaises(client.DownloadError):
            self.iq.fetch(client.get_url("/IDONOTEXIST"))

    @test.use_cache
    def test_fetch_no_cache(self):
        p = test.get_latest_presentation(self.iq)
        content = self.iq.fetch_no_cache(p.metadata['slides'][0])
        self.assertIsInstance(content, basestring)
        self.assertGreater(len(content), 1000)

    @test.use_cache
    def test_fetch_no_cache_error(self):
        with self.assertRaises(client.DownloadError):
            self.iq.fetch_no_cache(client.get_url("/IDONOTEXIST"))


class TestDownload(unittest2.TestCase):

    def setUp(self):
        self.iq = client.InfoQ()
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def assert_tmp_dir_nb_files(self, n):
        self.assertEqual(len(os.listdir(self.tmp_dir)), n)

    def assert_tmp_dir_is_empty(self):
        self.assert_tmp_dir_nb_files(0)

    @test.use_cache
    def test_download(self):
        p = test.get_latest_presentation(self.iq)

        self.assert_tmp_dir_is_empty()
        self.iq.download(p.metadata['slides'][0], self.tmp_dir)
        self.assert_tmp_dir_nb_files(1)
        self.iq.download(p.metadata['url'], self.tmp_dir)
        self.assert_tmp_dir_nb_files(2)
        with self.assertRaises(client.DownloadError):
            self.iq.download(client.get_url("/IDONOTEXIST"), self.tmp_dir)
        self.assert_tmp_dir_nb_files(2)

    @test.use_cache
    def test_download_override(self):
        p = test.get_latest_presentation(self.iq)

        self.assert_tmp_dir_is_empty()
        self.iq.download(p.metadata['slides'][0], self.tmp_dir)
        self.assert_tmp_dir_nb_files(1)
        self.iq.download(p.metadata['slides'][0], self.tmp_dir)
        self.assert_tmp_dir_nb_files(1)

    @test.use_cache
    def test_download_custom_name(self):
        p = test.get_latest_presentation(self.iq)

        self.assert_tmp_dir_is_empty()
        self.iq.download(p.metadata['slides'][0], self.tmp_dir)
        self.assert_tmp_dir_nb_files(1)
        self.iq.download(p.metadata['slides'][0], self.tmp_dir, filename="toto")
        self.assert_tmp_dir_nb_files(2)
        self.assertIn("toto", os.listdir(self.tmp_dir))

    def test_download_all(self):
        p = test.get_latest_presentation(self.iq)
        n = min(len(p.metadata['slides']), 5)

        self.assert_tmp_dir_is_empty()
        self.iq.download_all(p.metadata['slides'][:n], self.tmp_dir)
        self.assert_tmp_dir_nb_files(n)



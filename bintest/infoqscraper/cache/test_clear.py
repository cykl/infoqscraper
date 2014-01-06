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
import os
import shutil
import subprocess
import tempfile

from infoqscraper import client

from bintest.infoqscraper import TestInfoqscraper


usage_prefix = "usage: infoqscraper cache clear"


class TestArguments(TestInfoqscraper):

    def setUp(self):
        self.default_args = ['cache', 'clear']

    def test_help(self):
        output = self.run_cmd(self.default_args + ['--help'])
        self.assertTrue(output.startswith(usage_prefix))

    def test_clear(self):
        # Ensure there is at least one file in the cache dir
        infoq_client = client.InfoQ(cache_enabled=True)
        infoq_client.cache.put_content("testfile", b"content")

        # Backup the cache dir
        backup_dir = infoq_client.cache.dir
        tmp_dir = os.path.join(tempfile.mkdtemp(), os.path.basename(backup_dir))
        shutil.copytree(backup_dir, tmp_dir)

        try:
            self.run_cmd(self.default_args)
            self.assertFalse(os.path.exists(backup_dir))
            # Now restore the cache dir
            shutil.copytree(tmp_dir, backup_dir)
        finally:
            shutil.rmtree(os.path.dirname(tmp_dir))

    def test_extra_arg(self):
        try:
            self.run_cmd(self.default_args + ['extra_args'])
            self.fail("Exception expected")
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2)
            print(e.output)
            self.assertTrue(e.output.decode('utf8').startswith(usage_prefix))


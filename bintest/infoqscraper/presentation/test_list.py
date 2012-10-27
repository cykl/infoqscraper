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
import bintest
from infoqscraper import client
from infoqscraper import presentation
import subprocess


usage_prefix = "usage: infoqscraper presentation"

class TestArguments(bintest.infoqscraper.TestInfoqscraper):

    def build_list_cmd(self, args):
        return self.build_cmd([]) + ['-c', 'presentation', 'list'] + args

    def test_help(self):
        cmd =  self.build_list_cmd(['--help'])
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.assertTrue(output.startswith(usage_prefix))

    def test_no_arg(self):
        cmd = self.build_list_cmd([])
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.assertEqual(output.count("Id: "), 10)

    def test_max_hit(self):
        cmd = self.build_list_cmd(['-n', '1'])
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.assertEqual(output.count("Id: "), 1)

    def test_max_pages(self):
        cmd = self.build_list_cmd(['-m', '1'])
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.assertEqual(output.count("Id: "), presentation._RightBarPage.RIGHT_BAR_ENTRIES_PER_PAGES)

    def test_pattern(self):
        infoq_client = client.InfoQ(cache_enabled=True)
        summary = presentation.get_summaries(infoq_client).next()

        cmd = self.build_list_cmd(['-p', summary['title']])
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.assertEqual(output.count("Id: "), 1)

    def test_short_output(self):
        cmd = self.build_list_cmd(['-s'])
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        self.assertEqual(len(output.strip().split("\n")), 10)

    def test_duplicates(self):
        # Try to spot bugs in the summary fetcher.
        # Sometimes the same summary is returned several times
        cmd = self.build_list_cmd(['-n', '30', '-s'])
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).strip()
        ids = output.split('\n')
        id_set = set(ids)
        self.assertEqual(len(ids), len(id_set))

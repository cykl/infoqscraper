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
from infoqscraper import scrap

from bintest.infoqscraper import TestInfoqscraper

usage_prefix = "usage: infoqscraper presentation"


class TestArguments(TestInfoqscraper):

    def setUp(self):
        self.default_cmd = ["-c", "presentation", "list"]

    def test_help(self):
        output = self.run_cmd(self.default_cmd + ["--help"])
        self.assertTrue(output.startswith(usage_prefix))

    def test_no_arg(self):
        output = self.run_cmd(self.default_cmd)
        self.assertEqual(output.count("Id: "), 10)

    def test_max_hit(self):
        output = self.run_cmd(self.default_cmd + ["-n", "1"])
        self.assertEqual(output.count("Id: "), 1)

    def test_max_pages(self):
        output = self.run_cmd(self.default_cmd + ["-m", "1"])
        # Nowadays, the /presentations page contains more than 10 entries
        # The number of returned items is then determined by the implicit
        # -n 10 parameter
        self.assertEqual(output.count("Id: "), 10)

    def test_pattern(self):
        infoq_client = client.InfoQ(cache_enabled=True)
        summary = next(scrap.get_summaries(infoq_client))

        # Nowadays, the /presentations page contains more than 10 entries
        output = self.run_cmd(self.default_cmd + ["-p", summary['title']])
        self.assertEqual(output.count("Id: "), 1)

    def test_short_output(self):
        output = self.run_cmd(self.default_cmd + ["-s"])
        self.assertEqual(len(output.strip().split("\n")), 10)

    def test_duplicates(self):
        # Try to spot bugs in the summary fetcher.
        # Sometimes the same summary is returned several times
        output = self.run_cmd(self.default_cmd + ["-n", "30", "-s"])
        ids = output.split('\n')
        id_set = set(ids)
        self.assertEqual(len(ids), len(id_set))

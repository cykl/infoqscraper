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
import subprocess
import re

from infoqscraper import utils

usage_prefix = "usage: infoqscraper cache size"

class TestArguments(bintest.infoqscraper.TestInfoqscraper):

    def build_size_cmd(self, args):
        return self.build_cmd([]) + ['cache', 'size'] + args

    def test_help(self):
        cmd =  self.build_size_cmd(['--help'])
        output = utils.check_output(cmd, stderr=subprocess.STDOUT)
        self.assertTrue(output.startswith(usage_prefix))

    def test_size(self):
        # TODO: Find a better test
        # We could use du -sh then compare its output to our.
        cmd =  self.build_size_cmd([])
        output = utils.check_output(cmd, stderr=subprocess.STDOUT).strip()
        self.assertIsNotNone(re.match('\d{1,3}\.\d{2} \w{2,5}', output))

    def test_extra_arg(self):
        cmd = self.build_size_cmd(["extra_args"])
        try:
            output = utils.check_output(cmd, stderr=subprocess.STDOUT)
            self.fail("Exception expected")
        except subprocess.CalledProcessError as e:
            self.assertEqual(e.returncode, 2)
            print e.output
            self.assertTrue(e.output.startswith(usage_prefix))


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

import datetime
import six

from infoqscraper import client
from infoqscraper import presentation
from infoqscraper import test

from infoqscraper.test.compat import unittest


class TestSummaries(unittest.TestCase):
    def setUp(self):
        self.iq = client.InfoQ()

    def assert_valid_summary(self, summary):
        self.assertIsInstance(summary['id'], six.string_types)
        self.assertGreater(len(summary['id']), 3)

        self.assertIsInstance(summary['url'], six.string_types)
        self.assertTrue(summary['url'].startswith("http://"))
        self.iq.fetch(summary['url'])

        self.assertIsInstance(summary['desc'], six.string_types)
        self.assertGreater(len(summary['desc']), 5)

        self.assertIsInstance(summary['auth'], six.string_types)
        self.assertGreater(len(summary['auth']), 5)

        self.assertIsInstance(summary['date'], datetime.datetime)

        self.assertIsInstance(summary['title'], six.string_types)
        self.assertGreater(len(summary['title']), 5)

    @test.use_cache
    def test_summaries(self):
        summaries = presentation.get_summaries(self.iq)
        for i in range(12):
            summary = next(summaries)
            self.assert_valid_summary(summary)

    @test.use_cache
    def test_summaries_max_pages(self):
        # Check that only one page is fetched
        count = 0
        for summary in presentation.get_summaries(self.iq, filter=presentation.MaxPagesFilter(1)):
            self.assert_valid_summary(summary)
            # The number of presentation per page to be updated from time to time
            # We expect that the number of presentation will never be greater than
            # this magic number
            self.assertLessEqual(count, 20)
            count += 1


class TestPresentation(unittest.TestCase):
    def setUp(self):
        self.iq = client.InfoQ()

    def assertValidPresentationMetadata(self, m):
        # Audio and Pdf are not always available
        self.assertGreaterEqual(len(m), 13)
        self.assertLessEqual(len(m), 15)

        self.assertIsInstance(m['title'], six.string_types)

        self.assertIsInstance(m['date'], datetime.datetime)

        #self.assertIsInstance(m['duration'], int)

        self.assertIsInstance(m['summary'], six.string_types)

        self.assertIsInstance(m['bio'], six.string_types)

        self.assertIsInstance(m['about'], six.string_types)

        self.assertIsInstance(m['timecodes'], list)
        prev = -1
        for t in m['timecodes']:
            self.assertIsInstance(t, int)
            self.assertGreater(t, prev)
            prev = t

        self.assertIsInstance(m['slides'], list)
        for s in m['slides']:
            self.assertIsInstance(s, six.string_types)
            self.assertTrue(s.startswith("http://"))
        self.assertEqual(len(m['timecodes']), len(m['slides']) + 1)

        self.assertIsInstance(m['video_url'], six.string_types)
        self.assertTrue(m['video_url'].startswith("rtmpe://"))
        self.assertIsInstance(m['video_path'], six.string_types)
        self.assertTrue(m['video_path'].startswith("mp4:") or m['video_path'].startswith("flv:"))

        if 'mp3' in m:
            self.assertIsInstance(m['mp3'], six.string_types)

        if 'pdf' in m:
            self.assertIsInstance(m['pdf'], six.string_types)

    @test.use_cache
    def test_presentation_java_gc_azul(self):
        p = presentation.Presentation(self.iq, "Java-GC-Azul-C4")

        self.assertValidPresentationMetadata(p.metadata)

        self.assertEqual(p.metadata['title'], "Understanding Java Garbage Collection and What You Can Do about It")
        self.assertEqual(p.metadata['date'], datetime.datetime(2012, 10, 17))
        self.assertEqual(p.metadata['auth'], "Gil Tene")
        #self.assertEqual(p.metadata['duration'], 3469)
        self.assertEqual(p.metadata['summary'],
            "Gil Tene explains how a garbage collector works, covering the fundamentals, mechanism, terminology and metrics. He classifies several GCs, and introduces Azul C4.")
        self.assertEqual(p.metadata['bio'],
            "Gil Tene is CTO and co-founder of Azul Systems. He has been involved with virtual machine technologies for the past 20 years and has been building Java technology-based products since 1995. Gil pioneered Azul's Continuously Concurrent Compacting Collector (C4), Java Virtualization, Elastic Memory, and various managed runtime and systems stack technologies.")
        self.assertEqual(p.metadata['about'],
            'Software is changing the world; QCon aims to empower software development by facilitating the spread of knowledge and innovation in the enterprise software development community; to achieve this, QCon is organized as a practitioner-driven conference designed for people influencing innovation in their teams: team leads, architects, project managers, engineering directors.')
        self.assertEqual(p.metadata['timecodes'],
            [3, 15, 73, 143, 227, 259, 343, 349, 540, 629, 752, 755, 822, 913, 1043, 1210, 1290, 1360, 1386,
             1462, 1511, 1633, 1765, 1892, 1975, 2009, 2057, 2111, 2117, 2192, 2269, 2328, 2348, 2468, 2558,
             2655, 2666, 2670, 2684, 2758, 2802, 2820, 2827, 2838, 2862, 2913, 2968, 3015, 3056, 3076, 3113,
             3115, 3135, 3183, 3187, 3247, 3254, 3281, 3303, 3328, 3344, 3360, 3367, 3376, 3411, 3426, 3469])
        self.assertEqual(p.metadata['slides'],
            [client.get_url("/resource/presentations/Java-GC-Azul-C4/en/slides/%s.swf" % s) for s in
             list(range(1, 49)) + list(range(50, 51)) + list(range(52, 53)) + list(range(55, 65)) + list(range(66, 72))])
        self.assertEqual(p.metadata['video_url'],
                         "rtmpe://video.infoq.com/cfx/st/")
        self.assertEqual(p.metadata['video_path'],
                         "mp4:presentations/12-jun-everythingyoueverwanted.mp4")
        self.assertEqual(p.metadata['pdf'],
                         "http://www.infoq.com/pdfdownload.action?filename=presentations%2FQConNY2012-GilTene-EverythingyoueverwantedtoknowaboutJavaCollectionbutweretooafraidtoask.pdf")
        self.assertEqual(p.metadata['mp3'],
                         "http://www.infoq.com/mp3download.action?filename=presentations%2Finfoq-12-jun-everythingyoueverwanted.mp3")

    @test.use_cache
    def test_presentation_clojure_expression_problem(self):
        p = presentation.Presentation(self.iq, "Clojure-Expression-Problem")
        self.assertValidPresentationMetadata(p.metadata)
        self.assertTrue(p.metadata['video_path'].startswith("flv:"))

    @test.use_cache
    def test_presentation_latest(self):
        p = test.get_latest_presentation(self.iq)
        self.assertValidPresentationMetadata(p.metadata)


import datetime
import pprint
import os
import unittest2
import infoq

try:
    USERNAME = os.environ['INFOQ_USERNAME']
except KeyError:
    USERNAME = None

try:
    PASSWORD = os.environ['INFOQ_PASSWORD']
except  KeyError:
    PASSWORD = None

class TestInfoQ(unittest2.TestCase):
    def setUp(self):
        self.iq = infoq.InfoQ()

    def test_login_ok(self):
        if USERNAME and PASSWORD:
            self.iq._login(USERNAME, PASSWORD)

    def test_login_fail(self):
        self.assertRaises(Exception, self.iq._login, "user", "password")

    def test_rightbar_summaries(self):
        for index in xrange(2):
            rb = infoq.RightBarPage(1)
            rb.fetch()

            count = 0
            for entry in rb.summaries():
                count += 1
                self.assertIsNotNone(entry['id'])
                self.assertIsNotNone(entry['path'])
                self.assertIsNotNone(entry['desc'])
                self.assertIsNotNone(entry['auth'])
                self.assertIsNotNone(entry['date'])
                self.assertIsNotNone(entry['title'])

            self.assertGreaterEqual(count, infoq.RIGHT_BAR_ENTRIES_PER_PAGES)

    def test_presentation_summaries(self):
        count = 0
        for entry in self.iq.presentation_summaries():
            count += 1
            if count > infoq.RIGHT_BAR_ENTRIES_PER_PAGES * 3:
                break

    def test_presentation_summaries_custom_func(self):
        # Check that only fetch one page
        count = 0
        for entry in self.iq.presentation_summaries(filter=infoq.MaxPagesFilter(1)):
            self.assertLessEqual(count, infoq.RIGHT_BAR_ENTRIES_PER_PAGES)
            count += 1

        self.assertEqual(count, infoq.RIGHT_BAR_ENTRIES_PER_PAGES)


    def test_presentation(self):
        p = infoq.Presentation("Java-GC-Azul-C4")

        metadata = p.get_metadata()
        self.assertEqual(metadata['title'], "Understanding Java Garbage Collection and What You Can Do about It")
        self.assertEqual(metadata['date'], datetime.datetime(2012, 10, 17))
        self.assertEqual(metadata['auth'], "Gil Tene")
        self.assertEqual(metadata['duration'], 3469)
        self.assertEqual(metadata['sections'], ['Architecture & Design', 'Development'])
        self.assertItemsEqual(metadata['topics'], ['Azul Zing' , 'Azul' , 'JVM' , 'Virtual Machines' , 'Runtimes' , 'Java' , 'QCon New York 2012' , 'GarbageCollection' , 'QCon'])
        self.assertItemsEqual(metadata['summary'], "Gil Tene explains how a garbage collector works, covering the fundamentals, mechanism, terminology and metrics. He classifies several GCs, and introduces Azul C4.")
        self.assertEqual(metadata['bio'], "Gil Tene is CTO and co-founder of Azul Systems. He has been involved with virtual machine technologies for the past 20 years and has been building Java technology-based products since 1995. Gil pioneered Azul's Continuously Concurrent Compacting Collector (C4), Java Virtualization, Elastic Memory, and various managed runtime and systems stack technologies.")
        self.assertEqual(metadata['about'], 'Software is changing the world; QCon aims to empower software development by facilitating the spread of knowledge and innovation in the enterprise software development community; to achieve this, QCon is organized as a practitioner-driven conference designed for people influencing innovation in their teams: team leads, architects, project managers, engineering directors.')


if __name__ == '__main__':
    unittest2.main()

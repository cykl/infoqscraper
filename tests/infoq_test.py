import os
import unittest
import infoq

USERNAME = os.environ['INFOQ_USERNAME']
PASSWORD = os.environ['INFOQ_PASSWORD']


class TestInfoQ(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()

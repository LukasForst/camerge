import unittest

from camerge import merge_calendars


class TestBuild(unittest.TestCase):

    def test_function_exists(self):
        calendar = merge_calendars([])
        self.assertNotEqual('', calendar)


if __name__ == '__main__':
    unittest.main()

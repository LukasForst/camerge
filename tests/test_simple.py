# the inclusion of the tests module is not meant to offer best practices for
# testing in general, but rather to support the `find_packages` example in
# setup.py that excludes installing the "tests" package

import unittest

from icalendar import Event


class TestSimple(unittest.TestCase):

    def test_add_one(self):
        e = Event()
        e.add('status', 'CONFIRMED')
        ne = __copy_event(e, ['status'])
        self.assertEqual(e.get('status'), ne.get('status'))


if __name__ == '__main__':
    unittest.main()

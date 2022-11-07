import unittest

from camerge import merge_calendars
from tests import data


class TestBasics(unittest.TestCase):

    def test_function_exists(self):
        calendar = merge_calendars([])
        self.assertNotEqual('', calendar)

    def test_can_parse_data(self):
        calendar = merge_calendars(
            [('data://BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:Merged Calendar\nEND:VCALENDAR\n', True)]
        )
        self.assertNotEqual('', calendar)

    def test_can_parse_file(self):
        calendar = merge_calendars(
            [(f'file://{data("small-calendar.ics")}', True)]
        )
        self.assertNotEqual('', calendar)

    def test_can_request_http_url(self):
        s = 'http://raw.githubusercontent.com/LukasForst/camerge/master/tests/data/small-calendar.ics'
        calendar = merge_calendars([(s, True)])
        self.assertNotEqual('', calendar)

    def test_can_request_https_url(self):
        s = 'https://raw.githubusercontent.com/LukasForst/camerge/master/tests/data/small-calendar.ics'
        calendar = merge_calendars([(s, True)])
        self.assertNotEqual('', calendar)

    def test_can_request_webcal_url(self):
        s = 'webcal://raw.githubusercontent.com/LukasForst/camerge/master/tests/data/small-calendar.ics'
        calendar = merge_calendars([(s, True)])
        self.assertNotEqual('', calendar)

    def test_attendee_is_parsed_correctly(self):
        calendar = merge_calendars(
            calendar_data=[(f'file://{data("small-calendar.ics")}', True)],
            known_emails=['confirmed@example.com']
        )
        self.assertIn('STATUS:CONFIRMED', calendar)
        self.assertIn('SUMMARY:busy', calendar)
        self.assertIn('UID:4fdade89dd887bf4d663baa7bfb8f373@camerge', calendar)

        calendar = merge_calendars(
            calendar_data=[(f'file://{data("small-calendar.ics")}', True)],
            known_emails=['maybe@example.com']
        )
        self.assertIn('STATUS:TENTATIVE', calendar)
        self.assertIn('SUMMARY:busy', calendar)
        self.assertIn('UID:4fdade89dd887bf4d663baa7bfb8f373@camerge', calendar)

    def test_declined_event(self):
        calendar = merge_calendars(
            calendar_data=[(f'file://{data("declined-event.ics")}', True)],
            known_emails=['declined@example.com']
        )
        print(calendar)
        self.assertIn('STATUS:CANCELLED', calendar)
        self.assertIn('SUMMARY:busy', calendar)
        self.assertIn('UID:096c532031e4d1b56cff137b5ad6e656@camerge', calendar)


if __name__ == '__main__':
    unittest.main()

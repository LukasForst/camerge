import datetime

from fastapi import FastAPI, Response

from camerge import merge_calendars

app = FastAPI()


@app.get("/{full_path:path}")
async def calendar():
    """
    This method generates ical stream for any calendar app.
    """
    ical = merge_calendars(
        calendar_name='My Availability',
        calendar_domain='my.calendar.example.com',
        calendar_urls=[
            # take this google ical stream and anonymize events (no event names shown)
            ("https://calendar.google.com/calendar/ical/my@example.com/private-xxxxx/basic.ics", True),
            # take this event stream and do not anonymize event summary
            ("https://p30-caldav.icloud.com/published/2/xxxxxxxxx", False),
        ],
        # take event availability from these email addresses
        known_emails=[
            'me@example.com', 'otherme@example.com'
        ],
        # do not include events that are older than this
        skip_events_before=datetime.date(2021, 1, 1)
    )
    return Response(content=ical, media_type='text/calendar')

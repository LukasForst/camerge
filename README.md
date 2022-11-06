# Camerge

A simple tool for merging multiple calendars into one.
It also allows anonymization of the events, so nobody will be able to see the summary of the event.

What this solves:
You have multiple calendars, and you want to share availability in `ical` format with some other people.
This tool takes your private calendars (in `ical` format), merges them, optionally anonymize them and creates new `ical`
calendar with the correct availability data.

This project is a minimal library but can be very easily used as an API for example:

```python
import datetime
from fastapi import FastAPI, Response
from camerge import merge_calendars

app = FastAPI()


@app.get("/")
async def calendar():
    """
    This method generates ical data for any calendar app.
    """
    ical = merge_calendars(
        calendar_name='My Availability',
        calendar_domain='my.calendar.example.com',
        calendar_urls=[
            # take this google ical stream and anonymize events (no event names shown)
            ("https://calendar.google.com/calendar/ical/my@example.com/private-xxx/basic.ics", True),
            # take this event stream and do not anonymize event summary
            ("https://p30-caldav.icloud.com/published/2/xxx", False),
        ],
        # take event availability from these email addresses, these should be your own email addresses
        # associated with the claendar account
        known_emails=[
            'me@example.com', 'otherme@example.com'
        ],
        # do not include events that are older than this
        skip_events_before=datetime.date(2021, 1, 1)
    )
    return Response(content=ical, media_type='text/calendar')

```

## Dependencies

This project is based on [icalendar](https://github.com/collective/icalendar).

Requirements for the library:

```
icalendar==4.1.0
requests==2.28.1
```

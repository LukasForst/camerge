import logging
import uuid
from hashlib import md5
from typing import List, Optional, Callable, Tuple

import requests
from icalendar import Calendar, Event, Timezone
from icalendar.cal import Component

logger = logging.getLogger(__name__)


def copy_event(event: Event, keys: List[str]) -> Event:
    """
    Copies data with given keys from event to new Event instance.
    """
    copy = Event()
    for key in keys:
        if key in event:
            copy.add(key, event[key])
    return copy


def obfuscate_uid(maybe_uid: Optional[str], domain: str) -> str:
    """
    Obfuscates 'uid' property from the event.
    """
    # if the uid exist, we use it and run md5
    # if not, we generate uuid
    hashed_version = md5((maybe_uid if maybe_uid else str(uuid.uuid4())).encode(),
                         usedforsecurity=False).hexdigest()
    # and append used domain
    return f'{hashed_version}@{domain}'


def process_calendar_data(
        calendar_data: str,
        calendar_domain: str,
        busy_place_holder: Optional[str] = 'busy',
        event_mapper: Optional[Callable[[Event, Event], None]] = None
) -> List[Component]:
    """
    Processes given calendar data.
    :param calendar_data: string that contains raw ical data
    :param event_mapper: (newEvent, oldEvent) -> {modifications}
    :param calendar_domain domain to use for the new calendar events
    :param busy_place_holder when set to string, it replaces 'summary' in all events, when set
    to None, original 'summary' is used
    :return: list of new components
    """
    components = []
    loaded_calendar = Calendar().from_ical(calendar_data)
    for component in loaded_calendar.subcomponents:
        if isinstance(component, Timezone):
            # we include timezones by default, because there might be references
            components.append(component)
        elif isinstance(component, Event):
            # copy common data that we want
            event = copy_event(component, ['dtstart', 'dtend', 'dtstamp', 'rrule', 'status', 'summary'])
            # now obfuscate uid, so we don't disclose the original source
            event['uid'] = obfuscate_uid(event.get('uid', None), calendar_domain)
            # now we anonymize summary, if needed
            if busy_place_holder:
                event['summary'] = busy_place_holder
            # and map it if needed
            if event_mapper:
                event_mapper(event, component)
            components.append(event)
    return components


def get_calendar_data(ical_url: str) -> Optional[str]:
    """
    Downloads calendar from the given url or filesystem and returns calendar data.
    :param ical_url: https:// url OR file:// to download calendar
    :return: calendar string data or None if there was a problem downloading them
    """
    try:
        if ical_url.startswith('file://'):
            with open(ical_url[7:], 'r') as f:
                return f.read()
        else:
            r = requests.get(ical_url)
            return r.text
    except Exception as e:
        logger.exception(f'There was a problem when downloading calendar {ical_url[:10]}..', e)
    return None


def merge_calendars(
        calendar_urls: List[Tuple[str, bool]],
        calendar_name: str = 'Merged Calendar',
        busy_placeholder: str = 'busy',
        calendar_domain: str = 'camerge',
) -> str:
    """
    Takes calendar urls, downloads them and merges them.
    :param calendar_urls: tuple where first parameter is url and second option to anonymize data [url, shouldAnonymize]
    :param calendar_name name of the new calendar
    :param busy_placeholder when anonymizing the event what placeholder to use
    :param calendar_domain domain to use for the new calendar events
    :return: valid ical with merged calendars
    """
    calendar = Calendar()
    calendar.add('prodid', calendar_name)
    calendar.add('version', '2.0')
    # we go one
    for url, anonymize in calendar_urls:
        calendar_data = get_calendar_data(url)
        # if it was not possible to download it, we need to skip it
        if not calendar_data:
            continue
        # now we process all data and create components
        components = process_calendar_data(
            calendar_data=calendar_data,
            calendar_domain=calendar_domain,
            busy_place_holder=busy_placeholder if anonymize else None
        )
        # so we can add them to the calendar
        for component in components:
            calendar.add_component(component)
    return calendar.to_ical().decode()

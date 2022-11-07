import datetime
import logging
from hashlib import md5
from typing import List, Optional, Callable, Tuple, Union
from urllib.request import Request, urlopen

from icalendar import Calendar, Event, Timezone
from icalendar.cal import Component

logger = logging.getLogger(__name__)


def __copy_event(event: Event, keys: List[str]) -> Event:
    """
    Copies data with given keys from event to new Event instance.
    """
    copy = Event()
    for key in keys:
        if key in event:
            copy.add(key, event[key])
    return copy


def __generate_uid(component: Event, domain: str) -> str:
    """
    Obfuscates 'uid' property from the event.
    """
    # if the uid exist, we use it and run md5
    # if not, we use the whole event as a base for the md5
    hashed_version = md5((component['uid']
                          if 'uid' in component
                          else component.to_ical().decode()).encode()
                         ).hexdigest()
    # and append used domain
    return f'{hashed_version}@{domain}'


def __should_skip_event(component: Event, skip_events_before: datetime.date) -> bool:
    """
    Determines if the event should be skipped
    """
    # first we check if this event is worth using or not
    # we do not remove components that are recurring
    # TODO: remove even the recurring events as well in case they're no longer needed
    if skip_events_before and ('dtend' in component or 'dtstart' in component) and 'rrule' not in component:
        # try to get end of the event, if not possible, use event start
        event_end_date: Union[datetime.date, datetime.datetime] = \
            (component['dtend'] if 'dtend' in component else component['dtstart']).dt
        # two cases - datetime & time, we don't really care about the time
        if isinstance(event_end_date, datetime.datetime):
            event_end_date = event_end_date.date()
        # so we only compare dates
        if event_end_date < skip_events_before:
            return True
    return False


def __determine_status(component: Event, known_emails: List[str]) -> str:
    """
    Determines correct status for the new event.
    """
    if 'attendee' in component and len(known_emails) > 0:
        # first we need to ensure that attendees is a list
        attendees = component['attendee'] \
            if isinstance(component['attendee'], list) \
            else [component['attendee']]
        # then we obtain "raw" ical data as sometimes it's in 'email' field and sometimes in 'to_ical()'
        # gives us the email

        # get participation status for each attendee only in case the object has params, so we don't cause exception
        # and filter only cases where known email in either in email property or in the ical code
        # TODO: this part is not optimal (and quite slow)
        partstats = [a.params.get('partstat')
                     for a in attendees
                     if hasattr(a, 'params') and any(email in a.to_ical().decode().replace('\n', '')
                                                     for email in known_emails
                                                     )]
        # one of the known emails confirmed the event, thus the user is going
        if 'ACCEPTED' in partstats:
            return 'CONFIRMED'
        # if there's declined response, user is not going
        elif 'DECLINED' in partstats:
            return 'CANCELLED'
        # if it is tentative OR user didn't clarify it, event is tentative
        elif 'TENTATIVE' in partstats or 'NEEDS-ACTION' in partstats:
            return 'TENTATIVE'
    return component['status'] if 'status' in component else 'CONFIRMED'


def __process_calendar_data(
        calendar_data: str,
        calendar_domain: str,
        known_emails: List[str],
        skip_events_before: Optional[datetime.date],
        busy_place_holder: Optional[str],
        event_mapper: Optional[Callable[[Event, Event], None]] = None
) -> List[Component]:
    """
    Processes given calendar data.
    :param calendar_data: string that contains raw ical data
    :param calendar_domain domain to use for the new calendar events
    :param known_emails: email addresses of the user that owns this calendar, used to detect declined events
    :param skip_events_before: datetime including zone info, how old events can be skipped and not included in the calendar
    :param event_mapper: (newEvent, oldEvent) -> {modifications}
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
            if __should_skip_event(component, skip_events_before):
                continue
            # copy common data that we want
            # TODO: maybe investigate what is really needed and what is not
            event = __copy_event(component, [
                'dtstart', 'dtend', 'dtstamp', 'rrule', 'status', 'summary',
                'transp', 'sequence', 'recurrence-id'
            ])
            # now obfuscate uid, so we don't disclose the original source
            event['uid'] = __generate_uid(component, calendar_domain)
            # now we anonymize summary, if needed
            if busy_place_holder:
                event['summary'] = busy_place_holder
            # now we need to change status if the event was declined as cancelled
            event['status'] = __determine_status(component, known_emails)
            # and map it if needed
            if event_mapper:
                event_mapper(event, component)
            components.append(event)
    return components


def __get_calendar_data(calendar_data: str) -> Optional[str]:
    """
    Downloads calendar from the given url, filesystem or just returns data and returns calendar data.
    :param calendar_data: https:// url, file:// or data:// to download calendar
    :return: calendar string data or None if there was a problem downloading them
    """
    try:
        # process loading from the file
        if calendar_data.startswith('file://'):
            with open(calendar_data[7:], 'r') as f:
                return f.read()
        # process http request
        elif calendar_data.startswith('http') or calendar_data.startswith('webcal://'):
            # use http instead of webcal
            calendar_data = calendar_data.replace('webcal', 'http') \
                if calendar_data.startswith('webcal://') \
                else calendar_data
            # and then use standard library to request data
            with urlopen(Request(calendar_data)) as response:
                return response.read().decode()
        # process pure ical data
        elif calendar_data.startswith('data://'):
            return calendar_data[7:]
    except Exception as e:
        logger.exception(f'There was a problem when downloading calendar {calendar_data[:10]}..', e)
    return None


def merge_calendars(
        calendar_data: List[Tuple[str, bool]],
        known_emails: Optional[List[str]] = None,
        calendar_name: str = 'Merged Calendar',
        busy_placeholder: str = 'busy',
        calendar_domain: str = 'camerge',
        skip_events_before: Optional[datetime.date] = None
) -> str:
    """
    Takes calendar urls, downloads them and merges them.
    :param calendar_data: tuple where first parameter is calendar data (can be https://, file://, data://) and second
    option to anonymize data [calendar, shouldAnonymize]
    :param known_emails: email addresses of the user that owns this calendar, used to detect declined events
    :param calendar_name name of the new calendar
    :param busy_placeholder when anonymizing the event what placeholder to use
    :param calendar_domain domain to use for the new calendar events
    :param skip_events_before: datetime including zone info, how old events can be skipped and not included in ical
    :return: valid ical with merged calendars
    """
    calendar = Calendar()
    calendar.add('prodid', calendar_name)
    calendar.add('version', '2.0')
    # we go one
    for url, anonymize in calendar_data:
        calendar_data = __get_calendar_data(url)
        # if it was not possible to download it, we need to skip it
        if not calendar_data:
            continue
        # now we process all data and create components
        components = __process_calendar_data(
            calendar_data=calendar_data,
            calendar_domain=calendar_domain,
            known_emails=known_emails if known_emails else [],
            busy_place_holder=busy_placeholder if anonymize else None,
            skip_events_before=skip_events_before
        )
        # so we can add them to the calendar
        for component in components:
            calendar.add_component(component)
    return calendar.to_ical().decode()

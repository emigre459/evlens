from datetime import datetime, UTC

import pytz

from evlens.config import DATETIME_FORMAT


def get_current_datetime(date_delimiter="-", time_delimiter="_"):
    '''
    Gets the current UTC date and time.


    Parameters
    ----------
    date_delimiter: str. Should be a single character
        like "/" or "-". Indicates what to use as the
        separator character between days, months, and years.

    time_delimiter: str. Should be a single character
        like ":" or "_". Indicates what to use as the
        separator character between hours, minutes, 
        and seconds (e.g. string_delimiter=":" -> "08:00:00").


    Returns
    -------
    datetime.datetime if both delimiter args are None or 
    string object otherwise.
    '''

    current_datetime = datetime.now(UTC)

    if date_delimiter is not None or time_delimiter is not None:
        if date_delimiter is not None:
            date_format = f"%m{date_delimiter}%d{date_delimiter}%Y"

        else:
            date_format = "%m-%d-%Y"

        if time_delimiter is not None:
            time_format = f"%H{time_delimiter}%M{time_delimiter}%S"

        else:
            time_format = "%H_%M_%S"

        full_format = date_format + "_T" + time_format
        return current_datetime.strftime(full_format)

    else:
        return current_datetime

def get_current_time(string_delimiter="_"):
    '''
    Gets the current UTC time.


    Parameters
    ----------
    string_delimiter: str. Should be a single character
        like ":" or "_". Indicates what to use as the
        separator character between hours, minutes, 
        and seconds (e.g. string_delimiter=":" -> "08:00:00").


    Returns
    -------
    datetime.time or string object as described above.
    '''

    if string_delimiter is not None:
        time_format = f"%H{string_delimiter}%M{string_delimiter}%S"
        return datetime.now(UTC).time().strftime(time_format)

    else:
        return datetime.now(UTC).time()
    
def local_datetime_to_utc(local_datetime_str, local_timezone='US/Eastern'):
    
    # Make local time timezone-aware
    timezone = pytz.timezone(local_timezone)
    local_time = timezone.localize(
        datetime.strptime(local_datetime_str, "%m-%d-%Y %H:%M:%S")
    )
    
    return local_time.astimezone(pytz.UTC)
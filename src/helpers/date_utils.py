from datetime import datetime, timezone

def timestamp_as_datetime(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

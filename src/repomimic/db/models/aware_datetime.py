import datetime

from sqlalchemy import (
    TypeDecorator,
    DateTime
)

class AwareDateTime(TypeDecorator):
    """A TypeDecorator that ensures datetimes returned from the database
    are always timezone-aware (defaulting to UTC).
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert timezone-aware datetime to UTC naive datetime before saving,
        or pass it through if it's already naive.
        """
        if value is not None:
            if value.tzinfo is not None:
                value = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        """Explicitly attach the UTC timezone when pulling data out of the database."""
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value


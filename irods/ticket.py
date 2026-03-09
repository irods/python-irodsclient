import calendar
import contextlib
import datetime
import random
import string
from typing import Any, Optional, Type, Union  #  noqa: UP035

from irods.api_number import api_number
from irods.column import Column
from irods.message import TicketAdminRequest, iRODSMessage
from irods.models import TicketQuery


def get_epoch_seconds(utc_timestamp):
    epoch = None
    try:
        epoch = int(utc_timestamp)
    except ValueError:
        pass
    if epoch is not None:
        return epoch
    HUMAN_READABLE_DATE = "%Y-%m-%d.%H:%M:%S"
    try:
        x = datetime.datetime.strptime(utc_timestamp, HUMAN_READABLE_DATE)
        return calendar.timegm(x.timetuple())
    except ValueError:
        raise  # final try at conversion, so a failure is an error


def ticket_iterator(session, filter_args=()):
    """
    Enumerate the Tickets visible to the user.

    Args:
        session: an iRODSSession object with which to perform a query.
        filter_args: optional arguments for filtering the query.

    Returns:
        An iterator over a range of Ticket objects.
    """
    return (Ticket(session, result=row) for row in session.query(TicketQuery.Ticket).filter(*filter_args))


_COLUMN_KEY = Union[Column, Type[Column]]  # noqa: UP006


class Ticket:
    def __init__(self, session, ticket="", result: Optional[dict[_COLUMN_KEY, Any]] = None, allow_punctuation=False):  #  noqa: FA100
        """
        Initialize a Ticket object.  If no 'result' or 'ticket' string is provided, then generate a new
        Ticket string automatically.

        Args:
            session: an iRODSSession object through which API endpoints shall be called.
            ticket: an optional ticket string, if a particular one is desired for ticket creation or deletion.
            result: a row result from a query, containing at least the columns of irods.models.TicketQuery.Ticket.
            allow_punctuation: True if punctuation characters are to be allowed in generating a Ticket string.
                (By default, all characters will be digits or letters of the latin alphabet.)

        Raises:
            RuntimeError: if the given ticket parameter mismatches the result, or if result is of the wrong type.
        """
        self._session = session

        # Do an initial error and sanity check on result.
        try:
            if result is not None:
                _ticket = result[TicketQuery.Ticket.string]
        except (TypeError, KeyError) as exc:
            raise RuntimeError("If specified, 'result' parameter must be a TicketQuery.Ticket query result.") from exc

        # Process query result if given, and set object attributes from it.
        if result is not None:
            if _ticket != ticket != "":
                raise RuntimeError("A ticket name was specified but does not match the query result.")
            ticket = _ticket
            for attr, value in TicketQuery.Ticket.__dict__.items():
                if value is TicketQuery.Ticket.string:
                    continue
                if not attr.startswith("_"):
                    # backward compatibility with older schema versions
                    with contextlib.suppress(KeyError):
                        setattr(self, attr, result[value])

        self._ticket = (
            ticket if ticket else self._generate(allow_punctuation=allow_punctuation)
        )

    @property
    def session(self):
        return self._session

    @property
    def ticket(self):
        """Return the unique string associated with the ticket object."""
        return self._ticket

    # Provide 'string' property such that self.string is a synonym for self.ticket
    string = ticket

    def _generate(self, length=15, allow_punctuation=False):
        source_characters = string.ascii_letters + string.digits
        if allow_punctuation:
            source_characters += string.punctuation
        return "".join(
            random.SystemRandom().choice(source_characters) for _ in range(length)
        )

    def _api_request(self, cmd_string, *args, **opts):
        with self.session.pool.get_connection() as conn:
            self._lowlevel_api_request(conn, cmd_string, self.ticket, *args, **opts)
        return self

    @staticmethod
    def _lowlevel_api_request(conn_, cmd_string, ticket_string, *args, **opts):
        message_body = TicketAdminRequest(cmd_string, ticket_string, *args, **opts)
        message = iRODSMessage(
            "RODS_API_REQ", msg=message_body, int_info=api_number["TICKET_ADMIN_AN"]
        )
        conn_.send(message)
        response = conn_.recv()
        return response

    def issue(self, permission, target, **opt):
        return self._api_request("create", permission, target, **opt)

    create = issue

    def modify(self, *args, **opt):
        arglist = list(args)
        if arglist[0].lower().startswith("expir"):
            arglist[1] = str(get_epoch_seconds(utc_timestamp=arglist[1]))
        return self._api_request("mod", *arglist, **opt)

    def supply(self, **opt):
        self.session.ticket__ = self._ticket
        return self

    def delete(self, **opt):
        """
        Delete the iRODS ticket.

        This applies to a Ticket object on which issue() has been called or, as the case may
        be, to a Ticket initialized with a ticket string already existing in the object catalog.
        The deleted object is returned, but may not be used further except for local purposes
        such as extracting the string.  E.g.

            for t in tickets:
                print(t.delete().string, "being deleted")

        """
        return self._api_request("delete", **opt)

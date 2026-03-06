from irods.api_number import api_number
from irods.message import iRODSMessage, TicketAdminRequest
from irods.models import TicketQuery
from irods.column import Like, Column

from collections.abc import Mapping, Sequence
from typing import Any, Iterable, Optional, Type, Union

import random
import string
import logging
import datetime
import calendar


logger = logging.getLogger(__name__)


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

class default_ticket_query_factory:
    _callable = staticmethod(lambda session: session.query(TicketQuery.Ticket))
    def __call__(self, session):
        return self._callable(session)

def enumerate_tickets(session, *, query_factory=default_ticket_query_factory, raw=False):
    """
    Enumerates (via GenQuery1) all tickets visible by, or owned by, the current user.

    Args:
        session: An iRODSSession object for use in the query.
        query_factory: A class capable of generating a generic query or other iterable
            over TicketQuery.Ticket row results.
        raw: If false, transform each row returned into a Ticket object; else return
            the result rows unaltered.

    Returns:
        An iterator over a range of ticket objects.
    """
    query = query_factory()(session)

    if raw:
        yield from query
    else:
        yield from (Ticket(session, result=row) for row in query)

_column_lookup = dict[Type[Column], Any]

class Ticket:

    def __init__(self, 
                 session,
                 ticket="",
                 result: Optional[Union[_column_lookup, Iterable[_column_lookup]]] =None, # Optional (vs. '|') is Python 3.9 syntax
                 allow_punctuation=False):

        self._session = session

        try:
            if isinstance(result, Mapping):
                if (single_string:=result.get(TicketQuery.Ticket.string, '')):
                    if ticket and (ticket != single_string):
                        raise RuntimeError(
                            f"The specified result contained a ticket string mismatched to the provided identifier ({ticket = })"
                        )

            elif hasattr(result, '__iter__'):
                if ticket:
                    result = [row for row in result if row[TicketQuery.Ticket.string] == ticket][:1]

                if not result:
                    result = None
                else:
                    result = next(iter(result)) # result[0]

            if result:
                ticket = result[TicketQuery.Ticket.string]
                for attr, value in TicketQuery.Ticket.__dict__.items():
                    if value is TicketQuery.Ticket.string: continue
                    if not attr.startswith("_"):
                        try:
                            setattr(self, attr, result[value])
                        except KeyError:
                            # backward compatibility with older schema versions
                            pass

            self._ticket = ticket

        except TypeError:
            raise RuntimeError(
                "If specified, 'result' parameter must be a TicketQuery.Ticket search result or iterable of same"
            )

        except IndexError:
            raise RuntimeError(
                "If both result and string are specified, at least one 'result' must match the ticket string"
            )

        if not self._ticket:
            self._ticket = self._generate(allow_punctuation=allow_punctuation)

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

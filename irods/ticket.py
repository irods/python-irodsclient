from irods.api_number import api_number
from irods.message import iRODSMessage, TicketAdminRequest
from irods.models import TicketQuery
from irods.column import Like
from collections.abc import Mapping, Sequence

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


def list_tickets(session, *, raw=False, all=True):
    """
    Enumerates (via GenQuery1) all tickets visible by, or owned by, the current user.

    Args:
        session: An iRODSSession object for use in the query.
        raw: True if only the queried rows are to be returned; False to construct Ticket objects for each row.
        all: True if a comprehensive list is desired; otherwise only those
            tickets owned by the calling user.

    Returns:
        An iterator over a range of ticket objects.
    """
    query = session.query(TicketQuery.Ticket)
    if not all:
        query = query.filter(
            TicketQuery.Ticket.user_id == session.users.get(session.username).id
        )
    if raw:
        yield from query
    else:
        yield from (Ticket(session, result=_) for _ in query)


class Ticket:
    def __init__(self, session, ticket="", result=None, allow_punctuation=False):
        self._session = session
        try:
            if isinstance(result, Mapping):
                if (single_string:=result.get(TicketQuery.Ticket.string, '')):
                    if ticket and (ticket != single_string):
                        raise RuntimeError(
                            f"The specified result contained a ticket string mismatched to the provided identifier ({ticket = })"
                        )

            # Allow limited query for the purpose of populating id and other attributes
            if result == [] and ticket:
                result[:] = list(session.query(TicketQuery.Ticket).filter(TicketQuery.Ticket.string == ticket))

            if isinstance(result, Sequence):
                if ticket:
                    result = [_ for _ in result if _[TicketQuery.Ticket.string] == ticket][:1]

                if not result:
                    result = None
                else:
                    result = result[0]

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
        except TypeError:
            raise RuntimeError(
                "If specified, 'result' parameter must be a TicketQuery.Ticket search result or iterable of same"
            )
        except IndexError:
            raise RuntimeError(
                "If both result and string are specified, at least one 'result' must match the ticket string"
            )
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

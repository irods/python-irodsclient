from __future__ import absolute_import

from irods.api_number import api_number
from irods.message import iRODSMessage, TicketAdminRequest
from irods.models import TicketQuery

import random
import string
import logging
import datetime
import calendar


logger = logging.getLogger(__name__)


def get_epoch_seconds (utc_timestamp):
    epoch = None
    try:
        epoch = int(utc_timestamp)
    except ValueError:
        pass
    if epoch is not None:
        return epoch
    HUMAN_READABLE_DATE = '%Y-%m-%d.%H:%M:%S'
    try:
        x = datetime.datetime.strptime(utc_timestamp,HUMAN_READABLE_DATE)
        return calendar.timegm( x.timetuple() )
    except ValueError:
        raise # final try at conversion, so a failure is an error


class Ticket(object):
    def __init__(self, session,  ticket = '', result = None, allow_punctuation = False):
        self._session = session
        try:
            if result is not None: ticket = result[TicketQuery.Ticket.string]
        except TypeError:
            raise RuntimeError( "If specified, 'result' parameter must be a TicketQuery.Ticket search result")
        self._ticket = ticket if ticket else self._generate(allow_punctuation = allow_punctuation)

    @property
    def session(self):
        return self._session

    @property
    def ticket(self):
        """Return the unique string associated with the ticket object."""
        return self._ticket

    # Provide 'string' property such that self.string is a synonym for self.ticket
    string = ticket

    def _generate(self, length=15, allow_punctuation = False):
        source_characters = string.ascii_letters + string.digits
        if allow_punctuation:
            source_characters += string.punctuation
        return ''.join(random.SystemRandom().choice(source_characters) for _ in range(length))

    def _api_request(self,cmd_string,*args, **opts):
        message_body = TicketAdminRequest(self.session)(cmd_string, self.ticket, *args, **opts)
        message = iRODSMessage("RODS_API_REQ", msg=message_body, int_info=api_number['TICKET_ADMIN_AN'])

        with self.session.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()
        return self

    def issue(self,permission,target,**opt): return self._api_request("create",permission,target,**opt)

    create = issue

    def modify(self,*args,**opt):
        arglist = list(args)
        if arglist[0].lower().startswith('expir'):
            arglist[1] = str(get_epoch_seconds(utc_timestamp = arglist[1]))
        return self._api_request("mod",*arglist,**opt)

    def supply(self,**opt):
        object_ = self._api_request("session",**opt)
        self.session.ticket__ = self._ticket
        return object_

    def delete(self,**opt):
        """
        Delete the iRODS ticket.

        This applies to a Ticket object on which issue() has been called or, as the case may
        be, to a Ticket initialized with a ticket string already existing in the object catalog.
        The deleted object is returned, but may not be used further except for local purposes
        such as extracting the string.  E.g.

            for t in tickets:
                print(t.delete().string, "being deleted")

        """
        return self._api_request("delete",**opt)

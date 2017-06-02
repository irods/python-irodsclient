from __future__ import absolute_import
import random
import string
from irods.api_number import api_number
from irods.message import (
    iRODSMessage, TicketAdminRequest)

import logging

logger = logging.getLogger(__name__)


class Ticket(object):
    def __init__(self, session, ticket=None):
        self._session = session
        self._ticket = ticket if ticket else self.generate()

    @property
    def session(self):
        return self._session

    @property
    def ticket(self):
        return self._ticket


    def generate(self, length=15):
        return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits + string.punctuation) for _ in range(length))


    def supply(self):
        message_body = TicketAdminRequest("session", self.ticket)
        message = iRODSMessage("RODS_API_REQ", msg=message_body, int_info=api_number['TICKET_ADMIN_AN'])

        with self.session.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()


    def issue(self, permission, target):
        message_body = TicketAdminRequest("create", self.ticket, permission, target)
        message = iRODSMessage("RODS_API_REQ", msg=message_body, int_info=api_number['TICKET_ADMIN_AN'])

        with self.session.pool.get_connection() as conn:
            conn.send(message)
            response = conn.recv()

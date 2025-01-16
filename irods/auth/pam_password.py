import getpass
import logging
import ssl
import sys
from . import (__NEXT_OPERATION__, __FLOW_COMPLETE__,
    AuthStorage,
    authentication_base, _auth_api_request,
    throw_if_request_message_is_missing_key)
from .native import authenticate_native


def login(conn):
    ## short-cut back to the 4.2 logic:
    # conn._login_pam()

    authenticate_pam_password(conn,
        req = {'user_name': conn.account.proxy_user,
               'zone_name': conn.account.proxy_zone} )


_scheme = 'pam_password'


def get_pam_password_from_stdin(file_like_object = None):
    try:
        if file_like_object:
            sys.stdin = file_like_object
        if sys.stdin.isatty():
            return getpass.getpass('Please enter PAM Password: ')
        else:
            return sys.stdin.readline().strip()
    finally:
        sys.stdin = sys.__stdin__


def authenticate_pam_password( conn, req = None ):

    logging.info('----------- pam_password (begin)')

    if req is None:
        req = {'user_name': conn.account.proxy_user,
               'zone_name': conn.account.proxy_zone}

    _ = AuthStorage.create_temp_pw_storage(conn)

    pam_password_ClientAuthState(
        conn,
        scheme = _scheme
    ).authenticate_client(
        initial_request = req
    )

    logging.info('----------- pam_password (end)')


FORCE_PASSWORD_PROMPT = "force_password_prompt"
AUTH_PASSWORD_KEY = "a_pw"


class pam_password_ClientAuthState(authentication_base):

    def __init__(self, *a, check_ssl = True, **kw):
        super().__init__(*a,**kw)
        # TODO: Remove. This is only for debug & testing; check_ssl=False lets us send
        # password-related information in the clear (i.e. when SSL/TLS isn't active).
        self.check_ssl =  check_ssl

    def auth_client_start(self, request):
        if self.check_ssl:
            if not isinstance(self.conn.socket, ssl.SSLSocket):
                msg = 'Need to be connected via SSL.'
                raise RuntimeError(msg)

        resp = request.copy()

        obj = resp.pop(FORCE_PASSWORD_PROMPT, None)
        if obj:
            resp[AUTH_PASSWORD_KEY] = get_pam_password_from_stdin(file_like_object = obj if getattr(obj, 'readline', None)
                else None)
        else:
            pw = AuthStorage.get_env_password()
            if pw:
                resp[__NEXT_OPERATION__] = self.perform_native_auth
                return resp
            resp[AUTH_PASSWORD_KEY] = get_pam_password_from_stdin()

        resp[__NEXT_OPERATION__] = self.AUTH_CLIENT_AUTH_REQUEST
        return resp

    # Client define
    AUTH_CLIENT_AUTH_REQUEST = "pam_password_auth_client_request"
    # Server define
    AUTH_AGENT_AUTH_REQUEST = "auth_agent_auth_request"

    def pam_password_auth_client_request(self, request):
        server_req = request.copy()
        server_req[__NEXT_OPERATION__] = self.AUTH_AGENT_AUTH_REQUEST

        resp = _auth_api_request(self.conn, server_req)
        throw_if_request_message_is_missing_key(resp, {"request_result"})

        depot = AuthStorage.get_temp_pw_storage(self.conn)
        if depot:
            depot.store_pw(resp["request_result"])
        else:
            msg = "auth storage object was either not set, or allowed to expire prematurely."
            raise RuntimeError(msg)

        resp[__NEXT_OPERATION__] = self.perform_native_auth
        return resp

    def pam_password_auth_client_perform_native_auth(self, request):
        resp = request.copy()
        resp.pop(AUTH_PASSWORD_KEY, None)

        authenticate_native(self.conn, request)

        resp["next_operation"] = __FLOW_COMPLETE__
        self.loggedIn = 1;
        return resp

    perform_native_auth = pam_password_auth_client_perform_native_auth


import getpass
import logging
import ssl
import sys
from . import (__NEXT_OPERATION__, __FLOW_COMPLETE__,
    AuthStorage,
    authentication_base, _auth_api_request,
    throw_if_request_message_is_missing_key,
    CLIENT_GET_REQUEST_RESULT, FORCE_PASSWORD_PROMPT)

from .native import authenticate_native


def login(conn, **extra_opt):
    context_opt =  {'user_name': conn.account.proxy_user,'zone_name': conn.account.proxy_zone}
    context_opt.update(extra_opt)
    authenticate_pam_password(conn, req = context_opt)


_scheme = 'pam_password'


def authenticate_pam_password(conn):
    logging.info('----------- %s (begin)', _scheme)

    # By design, we persist this "depot" object over the whole of the authentication
    # exchange with the iRODS server as a means of sending password information to the
    # native phase of that process.  This has to be done in a way that preserves
    # the current environment (i.e. not writing to .irodsA) in the event that we
    # are authenticating without the help of iCommand-type client env/auth files.
    _ = AuthStorage.create_temp_pw_storage(conn)

    pam_password_ClientAuthState(
        conn,
        scheme = _scheme
    ).authenticate_client(
        initial_request = req
    )

    logging.info('----------- %s (end)', _scheme)


def get_pam_password_from_stdin(file_like_object = None):
    try:
        if file_like_object:
            if not getattr(file_like_object,'readline',None):
                msg = "The file_like_object, if provided, must have a 'readline' method."
                raise RuntimeError(msg)
            sys.stdin = file_like_object
        if sys.stdin.isatty():
            return getpass.getpass('Please enter PAM Password: ')
        else:
            return sys.stdin.readline().strip()
    finally:
        sys.stdin = sys.__stdin__


AUTH_PASSWORD_KEY = "a_pw"


class pam_password_ClientAuthState(authentication_base):

    def auth_client_start(self, request):
        if not isinstance(self.conn.socket, ssl.SSLSocket):
            msg = 'Need to be connected via SSL.'
            raise RuntimeError(msg)
        resp = request.copy()

        obj = resp.pop(FORCE_PASSWORD_PROMPT, None)
        if obj:
            obj = None if isinstance(obj,(int,bool)) else obj
            resp[AUTH_PASSWORD_KEY] = get_pam_password_from_stdin(file_like_object = obj)
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

        l = resp.pop(CLIENT_GET_REQUEST_RESULT,None)
        if isinstance(l,list):
            l[:] = (resp["request_result"],)

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


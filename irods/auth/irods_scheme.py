import ssl

from . import (
    __NEXT_OPERATION__,
    CLIENT_GET_REQUEST_RESULT,
    _auth_api_request,
    authentication_base,
)
from .pam_password import ENSURE_SSL_IS_ACTIVE

_scheme = "irods"


def login(conn, **extra_opt):
    request = {
        "user_name": conn.account.proxy_user,
        "zone_name": conn.account.proxy_zone
    }
    request.update(extra_opt)
    _irods_ClientAuthState(conn, scheme=_scheme).authenticate_client(initial_request=request)


class _irods_ClientAuthState(authentication_base):
    def auth_client_start(self, request):
        self._token_result = request.pop(CLIENT_GET_REQUEST_RESULT, None)

        if request.pop(ENSURE_SSL_IS_ACTIVE, True) and not isinstance(self.conn.socket, ssl.SSLSocket):
            msg = "irods auth scheme requires secure communications (TLS/SSL) with the server."
            raise RuntimeError(msg)

        resp = request.copy()
        resp[__NEXT_OPERATION__] = "client_init_auth_with_server"
        return resp

    def client_init_auth_with_server(self, request):
        server_req = request.copy()
        server_req[__NEXT_OPERATION__] = "server_prepare_auth_check"
        resp = _auth_api_request(self.conn, server_req)

        # set with set_auth_option_for_scheme("irods", "session_token", ...)
        if "session_token" in resp:
            resp[__NEXT_OPERATION__] = "client_auth_with_session_token"
        else:
            resp["password"] = self.conn.account.password or ""
            resp[__NEXT_OPERATION__] = "client_auth_with_password"
        return resp

    def client_auth_with_password(self, request):
        server_req = request.copy()
        server_req[__NEXT_OPERATION__] = "server_auth_with_password"
        resp = _auth_api_request(self.conn, server_req)

        if isinstance(self._token_result, list):
            self._token_result[:] = (resp["session_token"],)

        resp[__NEXT_OPERATION__] = "client_auth_with_session_token"
        return resp

    def client_auth_with_session_token(self, request):
        server_req = request.copy()
        server_req[__NEXT_OPERATION__] = "server_auth_with_session_token"
        resp = _auth_api_request(self.conn, server_req)
        self.loggedIn = 1
        return resp

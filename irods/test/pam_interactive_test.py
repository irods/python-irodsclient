import unittest
import os
import json
from irods.client_init import write_pam_interactive_irodsA_file
from unittest.mock import patch
from irods.auth import ClientAuthError, FORCE_PASSWORD_PROMPT
from irods.auth.pam_interactive import (
    _pam_interactive_ClientAuthState,
    PERFORM_WAITING,
    PERFORM_AUTHENTICATED,
    PERFORM_NEXT,
)
from irods.test.helpers import make_session
from irods.auth.pam_interactive import __NEXT_OPERATION__, __FLOW_COMPLETE__
from irods.auth.pam_interactive import _auth_api_request
class PamInteractiveTest(unittest.TestCase):

    def setUp(self):
        # These tests assume the irods_environment.json file is set up correctly
        # and that the iRODS user 'alice' exists in the 'tempZone' zone and has the password 'rods'.
        # There should also be a linux user 'alice' with the same password.
        self.sess = None
        self.auth_client = _pam_interactive_ClientAuthState(None, None, scheme="pam_interactive")
        self.env_file_path = os.path.expanduser("~/.irods/irods_environment.json")
        self.auth_file_path = os.path.expanduser("~/.irods/.irodsA")

        with open(self.env_file_path) as f:
            env = json.load(f)
        self.user = env.get("irods_user_name", "alice")
        self.zone = env.get("irods_zone_name", "tempZone")
        self.password = "rods"

    def tearDown(self):
        if self.sess:
            self.sess.cleanup()
        if os.path.exists(self.auth_file_path):
            os.remove(self.auth_file_path)

    def test_pam_interactive_login_basic(self):
        with patch("getpass.getpass", return_value=self.password):
            self.sess = make_session(test_server_version=False, env_file=self.env_file_path, authentication_scheme="pam_interactive")
            # Creating a session does not trigger auth, so the home collection is accessed to trigger and confirm auth succeeded
            home = self.sess.collections.get(f"/{self.sess.zone}/home/{self.sess.username}")
            self.assertEqual(home.name, self.sess.username)

    def test_pam_interactive_auth_file_creation(self):
        with patch("getpass.getpass", return_value=self.password):
            write_pam_interactive_irodsA_file(env_file=self.env_file_path)
            self.assertTrue(os.path.exists(self.auth_file_path), ".irodsA file was not created")

        with patch("getpass.getpass", return_value=self.password) as mock_getpass:
            self.sess = make_session(test_server_version=False, env_file=self.env_file_path, authentication_scheme= "pam_interactive")
            # Creating a session does not trigger auth, so the home collection is accessed to trigger and confirm auth succeeded
            home = self.sess.collections.get(f"/{self.sess.zone}/home/{self.sess.username}")
            self.assertEqual(home.name, self.sess.username)
            mock_getpass.assert_not_called()

    def test_forced_interactive_flow(self):
        with patch("getpass.getpass", return_value=self.password):
            write_pam_interactive_irodsA_file(env_file=self.env_file_path)
            self.assertTrue(os.path.exists(self.auth_file_path), ".irodsA file was not created")

        with patch("getpass.getpass", return_value=self.password) as mock_getpass:
            self.sess = make_session(test_server_version=False, env_file=self.env_file_path, authentication_scheme="pam_interactive")
            self.sess.set_auth_option_for_scheme("pam_interactive", FORCE_PASSWORD_PROMPT, True)
            # Creating a session does not trigger auth, so the home collection is accessed to trigger and confirm auth succeeded
            home = self.sess.collections.get(f"/{self.sess.zone}/home/{self.sess.username}")
            self.assertEqual(home.name, self.sess.username)
            mock_getpass.assert_called_once()

    def test_failed_login_incorrect_password(self):
        with patch("getpass.getpass", return_value="wrong_password"):
            with self.assertRaises(ClientAuthError):
                self.sess = make_session(test_server_version=False, env_file=self.env_file_path, authentication_scheme="pam_interactive")
                self.sess.collections.get(f"/{self.sess.zone}/home/{self.sess.username}")  # trigger auth flow

        with patch("getpass.getpass", return_value="wrong_password"):
            with self.assertRaises(ClientAuthError):
                write_pam_interactive_irodsA_file(env_file=self.env_file_path)

    def test_get_default_value(self):
        test_cases = [
            ("simple_path", {"msg": {"default_path": "/username"}, "pstate": {"username": "alice"}}, "alice"),
            ("nested_path", {"msg": {"default_path": "/user/name"}, "pstate": {"user": {"name": "alice"}}}, "alice"),
            ("path_does_not_exist", {"msg": {"default_path": "/user/username"}, "pstate": {"username": "alice"}}, ""),
            ("non_string_value", {"msg": {"default_path": "/user/id"}, "pstate": {"user": {"id": 123}}}, "123"),
            ("no_default_path", {"msg": {}, "pstate": {"username": "alice"}}, ""),
        ]

        for name, request, expected in test_cases:
            with self.subTest(name=name):
                self.assertEqual(self.auth_client._get_default_value(request), expected)

    def test_patch_state(self):
        test_cases = [
            ("add_op", {"msg": {"patch": [{"op": "add", "path": "/username", "value": "alice"}]}, "pstate": {}}, {"username": "alice"}, True),
            ("replace_op", {"msg": {"patch": [{"op": "replace", "path": "/username", "value": "rods"}]}, "pstate": {"username": "alice"}}, {"username": "rods"}, True),
            ("remove_op", {"msg": {"patch": [{"op": "remove", "path": "/username"}]}, "pstate": {"username": "rods"}}, {}, True),
            ("add_resp_fallback", {"msg": {"patch": [{"op": "add", "path": "/username"}]}, "pstate": {}, "resp": "alice"}, {"username": "alice"}, True),
            ("replace_resp_fallback", {"msg": {"patch": [{"op": "replace", "path": "/username"}]}, "pstate": {"username": "rods"}, "resp": "alice"}, {"username": "alice"}, True),
            ("nested_add_operation", {'msg': {'patch': [{'op': 'add', 'path': '/user/name', 'value': 'alice'}]}, 'pstate': {'user': {}}}, {'user': {'name': 'alice'}}, True),
            ("resp_fallback_empty", {'msg': {'patch': [{'op': 'add', 'path': '/username'}]}, 'pstate': {}}, {'username': ''}, True),
            ("no_patch_ops", {"msg": {}, "pstate": {"username": "alice"}, "pdirty": False}, {"username": "alice"}, False)
        ]

        for name, request, expected_pstate, expected_pdirty in test_cases:
            with self.subTest(name=name):
                self.auth_client._patch_state(request)
                self.assertEqual(request["pstate"], expected_pstate)
                self.assertEqual(request["pdirty"], expected_pdirty)

    def test_retrieve_entry(self):
        test_cases = [
            ("surface_value", {"msg": {"retrieve": "/user"}, "pstate": {"user": "alice"}}, True, "alice"),
            ("nested_value", {"msg": {"retrieve": "/user/password"}, "pstate": {"user": {"password": "rods"}}}, True, "rods"),
            ("empty_value", {"msg": {"retrieve": "/user"}, "pstate": {"user": ""}}, True, ""),
            ("path_does_not_exist", {"msg": {"retrieve": "/missing"}, "pstate": {"user": "alice"}}, True, ""),
            ("non_string_value", {'msg': {'retrieve': '/user/id'}, 'pstate': {'user': {'id': 456}}}, True, '456'),
            ("no_retrieve_key", {"msg": {}, "pstate": {"user": "alice"}}, False, None)
        ]

        for name, request, expected_result, expected_resp in test_cases:
            with self.subTest(name=name):
                self.assertEqual(self.auth_client._retrieve_entry(request), expected_result)
                if expected_result:
                    self.assertEqual(request["resp"], expected_resp)

    @patch('irods.auth.pam_interactive._auth_api_request', return_value={"result": "ok"})
    @patch('sys.stderr.write')
    def test_get_input(self, mock_stderr, mock_api_request):
        test_cases = [
            ("non_password_input", False, 'sys.stdin.readline', "rods\n", {"msg": {"prompt": "Prompt:"}}, "rods"),
            ("non_password_default", False, 'sys.stdin.readline', "\n", {"msg": {"prompt": "Prompt:", "default_path": "/password"}, "pstate": {"password": "rods"}}, "rods"),
            ("password_input", True, 'getpass.getpass', "rods", {"msg": {"prompt": "Password:"}}, "rods"),
            ("password_default", True, 'getpass.getpass', "", {"msg": {"prompt": "Password:", "default_path": "/password"}, "pstate": {"password": "rods"}}, "rods")
        ]

        for name, is_password, mock_target, user_input, request, expected_resp in test_cases:
            with self.subTest(name=name), patch(mock_target, return_value=user_input), patch.object(self.auth_client, '_patch_state') as mock_patch:
                resp = self.auth_client._get_input(request, is_password=is_password)
                self.assertEqual(request["resp"], expected_resp)
                self.assertEqual(resp, {"result": "ok"})
                mock_patch.assert_called_once()

    def test_pass_through_states(self):
        with patch("irods.auth.pam_interactive._auth_api_request", return_value={"result": "ok"}):
            request = {"msg": {"prompt": "Prompt:"}, "pstate": {}, "pdirty": False}
            for state in [self.auth_client.next, self.auth_client.running, self.auth_client.ready, self.auth_client.response]:
                with self.subTest(state=state.__name__):
                    resp = state(request)
                    self.assertEqual(resp, {"result": "ok"})

    def test_failure_states(self):
        request = {"foo": "bar"}
        with patch("irods.auth.pam_interactive._logger"):
            for state in [self.auth_client.error, self.auth_client.timeout, self.auth_client.not_authenticated]:
                with self.subTest(state=state.__name__):
                    resp = state(request)
                    self.assertEqual(resp[__NEXT_OPERATION__], __FLOW_COMPLETE__)
                    self.assertEqual(self.auth_client.loggedIn, 0)

    @patch("sys.stdin.readline", return_value="ABC123\n")
    def test_pam_interactive_mfa_flow(self, mock_stdin):
        state = {"stage": "before_mfa", "step": 0}

        def mock_server(conn, req):
            # Switch from the real server to the mock server when the password step is completed
            if state["stage"] == "before_mfa":
                resp = _auth_api_request(conn, req)
                if req.get(__NEXT_OPERATION__) == PERFORM_NEXT: # Indicates the password step is complete
                    state["stage"] = "mfa_mock"
                return resp

            # MFA simulation steps
            if state["step"] == 0:
                return {
                    __NEXT_OPERATION__: PERFORM_WAITING,
                    "pstate": {"Password: ": self.password, "verification_code": ""},
                    "msg": {
                        "prompt": "Verification Code: ",
                        "default_path": "/verification_code",
                        "patch": [{"op": "add", "path": "/verification_code"}],
                    },
                    "pdirty": True,
                }
            elif state["step"] == 1:
                return {
                    __NEXT_OPERATION__: PERFORM_NEXT,
                    "pstate": {"Password: ": self.password, "verification_code": ""},
                    "pdirty": True,
                }
            elif state["step"] == 2:
                return {
                    __NEXT_OPERATION__: PERFORM_AUTHENTICATED,
                    "pstate": {"Password: ": self.password, "verification_code": "ABC123"},
                    "pdirty": True,
                    "request_result": "temp_token",
                }

            state["step"] += 1

        with patch("irods.auth.pam_interactive._auth_api_request", side_effect=mock_server), \
            patch("getpass.getpass", return_value=self.password), \
            patch("irods.auth.pam_interactive._authenticate_native") as mock_native:

            self.sess = make_session(test_server_version=False, env_file=self.env_file_path, authentication_scheme="pam_interactive")
            self.sess.server_version  # Trigger auth flow

        mock_native.assert_called_once()

if __name__ == "__main__":
    unittest.main()
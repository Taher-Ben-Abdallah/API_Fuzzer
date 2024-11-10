from typing import Dict, List

from httpx import (
    Auth as HttpxAuth,
    DigestAuth as HttpxDigestAuth,
)
import httpx_auth
import httpx_ntlm
import jwt

from fuzzer_core.engine.requester.types_modes import AuthMode


class AnyCustomAuth(HttpxAuth, httpx_auth.SupportMultiAuth):
    """
    Template for adding custom authentication to the request
    Pass the needed parameters to the constructor
    Add the needed information to the request through auth_flow method
    """

    def __init__(self):
        pass

    def auth_flow(self, request):
        # Example:
        # Send the request, with an authentication header.
        # request.headers['X-Authentication'] = self.token
        yield request


class CustomAuth(HttpxAuth, httpx_auth.SupportMultiAuth):

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def auth_flow(self, request):
        # Example:
        # Send the request, with an authentication header.
        request.headers[self.key] = self.value
        yield request


class BearerAuth(HttpxAuth, httpx_auth.SupportMultiAuth):
    def __init__(self, token):
        self.token = token

    def auth_flow(self, request):
        # Example:
        # Send the request, with an authentication header.
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


class JWTAuth(HttpxAuth, httpx_auth.SupportMultiAuth):
    def __init__(self, token_info: str | dict, action: str = "use-jwt"):
        try:
            if action == "use-jwt":
                assert isinstance(token_info, str)
                self.token = token_info
            if action == "generate-jwt":
                assert isinstance(token_info, dict)
                assert isinstance(token_info["payload"], dict)
                self.token = jwt.encode(payload=token_info["payload"], key=token_info["secret"],
                                        algorithm=token_info["algorithm"])
        except AssertionError:
            raise ValueError("JWT token information is invalid")

    def auth_flow(self, request):
        request.headers['Authorization'] = f'Bearer {self.token}'
        yield request


class DigestAuth(HttpxDigestAuth, httpx_auth.SupportMultiAuth):
    """Enabling Multi Authentication support for httpx DigestAuth"""

    def __init__(self, username: str | bytes, password: str | bytes):
        HttpxDigestAuth.__init__(self, username, password)


class NTLMAuth(httpx_ntlm.HttpNtlmAuth, httpx_auth.SupportMultiAuth):
    """Enabling Multi Authentication support for httpx NTLM authentication"""

    def __init__(self, username: str, password: str):
        httpx_ntlm.HttpNtlmAuth.__init__(self, username, password)


################################################################

def prepare_auth(auth: Dict[AuthMode | str, Dict] | List[Dict]):
    """
    A function to prepare authentication needed for the requests \n
    Authentication information is in a dictionary \n
    Multiple authentication methods (list of dicts) are handled recursively \n
    Custom authentication methods should inherit from httpx_auth.SupportMultiAuth to support Multiple authentication \n

    :param auth: authentication information
    :return: httpx.Auth object
    """

    # httpx_auth documentation : https://colin-b.github.io/httpx_auth
    # httpx_ntlm documentation : https://github.com/ulodciv/httpx-ntlm

    # TODO: Add Exception Handling

    if isinstance(auth, list):
        if len(auth) == 1:
            return prepare_auth(auth[0])
        return prepare_auth(auth[1:]) + prepare_auth(auth[0])

    if not isinstance(auth, dict):
        raise TypeError('Authentication info must be a dictionary')

    auth_mode = auth["auth_mode"].value if isinstance(auth["auth_mode"], AuthMode) else auth["auth_mode"]
    credentials = auth["credentials"]
    match auth_mode:
        case AuthMode.BASIC.value:
            """
            "credentials": { "username": ..., "password": ... }
            """
            return httpx_auth.Basic(username=credentials['username'], password=credentials['password'])

        case AuthMode.DIGEST.value:
            """
            "credentials": { "username": ..., "password": ... }
            """
            return DigestAuth(username=credentials['username'], password=credentials['password'])

        case AuthMode.BEARER.value:
            """
            "credentials": { "token": ...}
            """
            return BearerAuth(token=credentials['token'])

        case AuthMode.APIKEY.value:
            """
            "credentials": { "name": ... , "location": ... , "value": ... }
            """
            # API Key can be added to the request headers or parameters

            name = credentials.get("name", None)
            if credentials['location'] == "headers":
                return httpx_auth.HeaderApiKey(api_key=credentials["value"], header_name=name)
            if credentials['location'] == "params":
                return httpx_auth.QueryApiKey(api_key=credentials["value"], query_parameter_name=name)

        case AuthMode.JWT.value:
            """
            "credentials": { "token_info": ... , "action": ... }
            """
            return JWTAuth(token_info=credentials["token_info"], action=credentials["action"])

        case AuthMode.NTLM.value:
            """
            "credentials": { "domain": ... , "username": ... , "password": ... }
            """

            return NTLMAuth(username=f'{credentials["domain"]}\\{credentials["username"]}',
                            password=credentials['password'])
        case AuthMode.CUSTOM.value:
            """
            "credentials": { "key": ... , "value": ...}
            """
            return CustomAuth(key=credentials["key"], value=credentials["value"])

        case AuthMode.AWS.value:
            """
            "credentials": { "access_id": ... , "secret_key": ... , "region": ..., "service": ... }
            """
            return httpx_auth.AWS4Auth(access_id=credentials["access_id"],
                                       secret_key=credentials["secret_key"], region=credentials["region"],
                                       service=credentials["service"])
        case AuthMode.OAUTH2.value:
            # TODO: This
            pass
        case AuthMode.OAUTH1.value:
            # TODO: This
            pass


if __name__ == '__main__':

    # Define a function to run all test cases
    def run_auth_tests():
        # Test cases for each AuthMode
        test_cases = {
            AuthMode.BASIC: {
                "auth_mode": "Basic-auth",
                "credentials": {
                    "username": "test_user",
                    "password": "test_pass"
                }
            },
            AuthMode.DIGEST: {
                "auth_mode": AuthMode.DIGEST,
                "credentials": {
                    "username": "test_user",
                    "password": "test_pass"
                }
            },
            AuthMode.BEARER: {
                "auth_mode": AuthMode.BEARER,
                "credentials": {
                    "token": "test_token"
                }
            },
            AuthMode.APIKEY: {
                "auth_mode": AuthMode.APIKEY,
                "credentials": {
                    "name": "api_key_name",
                    "location": "headers",
                    "value": "api_key_value"
                }
            },
            AuthMode.JWT: {
                "auth_mode": AuthMode.JWT,
                "credentials": {
                    "token_info": "test_jwt_token",
                    "action": "use-jwt"
                }
            },
            AuthMode.AWS: {
                "auth_mode": AuthMode.AWS,
                "credentials": {
                    "access_id": "aws_access_id",
                    "secret_key": "aws_secret_key",
                    "region": "us-west-2",
                    "service": "execute-api"
                }
            },
            AuthMode.NTLM: {
                "auth_mode": AuthMode.NTLM,
                "credentials": {
                    "domain": "DOMAIN",
                    "username": "user",
                    "password": "pass"
                }
            },
            AuthMode.CUSTOM: {
                "auth_mode": AuthMode.CUSTOM,
                "credentials": {
                    "key": "X-Custom-Auth",
                    "value": "custom_value"
                }
            }
        }

        # Run each test case
        for auth_mode, auth_data in test_cases.items():
            try:
                print(f"\nTesting {auth_mode.value}")
                auth_obj = prepare_auth(auth_data)

                # Print the type and representation of the result for inspection
                print("Result:", type(auth_obj), auth_obj)
            except Exception as e:
                print(f"Error in {auth_mode.value}:", e)


    # Run the tests
    run_auth_tests()

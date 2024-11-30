import asyncio
import os
import tempfile
import time
from typing import Dict, Tuple, List

import httpx
from httpx import AsyncClient

from fuzzer_core.engine.queues.request_queue import RequestQueue
from fuzzer_core.engine.queues.response_queue import ResponseQueue
from fuzzer_core.engine.request_builder import RequestBuilder, merge_dicts
from fuzzer_core.engine.requester.auth import prepare_auth
from fuzzer_core.engine.requester.types_modes import AuthMode
from fuzzer_core.engine.ratelimiter import RateLimiter

import mimetypes
from fuzzer_core.engine.response_analyser import ResponseAnalyser, AnalysisOptions, ResponseNotMatchedExc
from utils.loaders import load_from_file


########################################################################

def generate_custom_file(*args):
    """
    Prepares a custom temporary file to be sent in a request
    the temporary file gets deleted once the stream closed
    :param file_content:
    :param file_name:
    :param file_type:
    :return: Tuple
    """
    file_content, file_name, file_type = args
    with tempfile.NamedTemporaryFile(mode='wb+', suffix=file_type) as temp_file:
        # Write the string content to the temporary file
        temp_file.write(file_content.encode('utf-8'))
        temp_file.seek(0)  # Move the file cursor to the beginning for reading

        # Prepare the file for sending in the request
        # return type should match one of the RequestFiles specified types : Tuple[str, FileTypes]] in this case
        return (file_name,
                (file_name, temp_file, mimetypes.mime_types[file_type])
                )


def prepare_files(files: List[Dict[str, str | None] | Tuple[str, str, str]]):
    """
    Method that prepares the files to be added to a request
    Files can be loaded and/or generated using generate_custom_file

    :param files: list of dicts (file path and optional filename)
    :return: list of tuples containing filename and file content
    """

    # TODO: Add ability to load generated Binary values for testing as file content
    file_list = []

    # if Item is a tuple, a file should be generated with values in tuple
    # if Item is a dict, it should be loaded from system
    for file in files:
        if isinstance(file, tuple):
            file_list.append(generate_custom_file(*file))

        if isinstance(file, dict):
            _, file_ext = os.path.splitext(file["file_path"])
            # return type should match one of the RequestFiles specified types : Tuple[str, FileTypes]] in this case
            file_list.append(
                (file.get("file_name", os.path.basename(file["file_path"])),
                 (file.get("file_name", os.path.basename(file["file_path"])),
                  load_from_file(file["file_path"], "rb"),
                  mimetypes.mime_types[file_ext]
                  )
                 )
            )

    return file_list


class Requester(AsyncClient):

    def __init__(self, base_url="", headers=None, auth: dict = None, cookies=None, timeout=None, follow_redirects=None,
                 proxy=None, http1=True, http2=False, config=None):
        """

        :param base_url:
        :param headers:
        :param auth:
        :param cookies:
        :param timeout:
        """

        self.auth = None
        if config:
            requester_conf = config.get('request', {})
            if config.get("proxy", None) is not None:
                requester_conf['proxy'] = config.get("proxy", None)
            if config.get("timeout", None) is not None:
                requester_conf['timeout'] = config.get("timeout", None)

            defined_params = {}
            for param_name in ['base_url', 'headers', 'auth', 'cookies', 'timeout', 'follow_redirects', 'proxy']:
                param_value = locals().get(param_name)
                if param_value is not None:
                    defined_params[param_name] = param_value

            print("defined PARAMS", defined_params)
            print("CONF:  ", requester_conf)

            merged = merge_dicts(defined_params, requester_conf)

            super().__init__(base_url=merged.get('base_url', ''), headers=merged.get('headers', None),
                             cookies=merged.get('cookies', None), params=merged.get('params', None),
                             follow_redirects=merged.get('follow_redirects', None), proxy=merged.get('proxy', None),
                             timeout=merged.get('timeout', None), http1=merged.get('http1', True),
                             http2=merged.get('http2', False))

            if merged.get('auth', None):
                self.auth = prepare_auth(merged.get['auth'])

        else:
            super().__init__(base_url=base_url, headers=headers, cookies=cookies, timeout=timeout,
                             follow_redirects=follow_redirects)
            if auth:
                self.auth = prepare_auth(auth)

    @staticmethod
    def reconstruct_response(response: httpx.Response) -> str:
        response_string = f"{response.http_version} {response.status_code} {response.reason_phrase}\n"
        response_string += ''.join(f"{key}: {value}\n" for key, value in response.headers.items())
        response_string += "\n" + response.text

        return response_string

    @staticmethod
    def reconstruct_request(request: httpx.Request) -> str:
        """
        Reconstruct an HTTP request into a string format for display.
        :param request: The httpx.Request instance to reconstruct.
        :return: A string representation of the HTTP request.
        """
        # Construct the request line with query parameters
        url_with_params = "Something"

        url_with_params = f"{request.url.scheme or ''}://{request.url.host}{':' + request.url.port if request.url.port is not None else ''}{request.url.path}"
        if request.url.query:
            url_with_params += f"?{request.url.query.decode('utf-8')}"

        # Start with the request line
        request_string = f"{request.method} {url_with_params} HTTP/{request.extensions.get('http_version', '1.1')}\n"

        # Add the headers
        request_string += ''.join(f"{key}: {value}\n" for key, value in request.headers.items())

        # Add a newline to separate headers from the body
        request_string += "\n"

        # Add the body content if it's present
        if request.content:
            request_string += request.content.decode() if isinstance(request.content, bytes) else str(request.content)

        return request_string

    async def prepare_and_send(self, req_dict):
        """
            This Async method takes the request details as parameters, prepares them and sends the request
        :param req_dict:
        :return: Response object
        """
        # Closing connection so the next request won't be sent under same connection (asyncio issues)
        headers = req_dict.get("headers", {})
        headers["Connection"] = "close"

        auth = self.auth
        if req_dict.get("auth", None) is not None:
            auth = prepare_auth(req_dict.get("auth")) + auth if auth is not None else prepare_auth(req_dict.get("auth"))

        response = await self.request(method=req_dict.get("method"), url=req_dict.get("url"), auth=auth,
                                      params=req_dict.get("params", None), headers=headers,
                                      cookies=req_dict.get("cookies", None), content=req_dict.get("content", None),
                                      data=req_dict.get("data", None), json=req_dict.get("json", None))

        return response

    async def send_request(self, req, auth) -> httpx.Response | None:
        """
        This method sends a built request and returns the response
        :param req: request object (built and ready to be sent)
        :param auth: authentication ( either of type AuthType or UseClientDefault)
        :return: response Object
        """
        try:
            response = await self.send(request=req, auth=auth, follow_redirects=self.follow_redirects)
        except httpx.ConnectError:
            # TODO: Log this error
            print("Error connecting to url")
            return None
        return response

    async def send_requests(self, request_list: list[dict] = None, rate_limiter=None, **kwargs) -> list[httpx.Response]:
        """
        Async method receives a list of request values and sends them with a defined delay
        :param request_list: list of dicts of request values
        :param rate_limiter: object to rate limit of requests sent to the target API
        :param kwargs: for sending a specific request a number of times ( 'iterations' key in kwargs)
        :return: list of responses
        """

        # TODO: if the method takes no input, raise an exception
        if request_list is None and not kwargs:
            return []

        response_list = []

        # will iterate over either the kwargs(one specific request) or the request_list
        # [kwargs] is a list of 1 item (dict)

        async with rate_limiter as limiter:
            # async with RateLimiter(rate_limit=rate_limiter) as limiter:
            for _ in range(kwargs.get("iterations", 1)):
                for request in request_list or [kwargs]:
                    # preparing and building request object
                    url = request.get("url", None)
                    method = request.get("method", None)
                    headers = request.get("headers", None)
                    auth = request.get("auth", None)
                    params = request.get("params", None)
                    content = request.get("content", None)
                    data = request.get("data", None)
                    json = request.get("json", None)
                    files = request.get("files", None)
                    cookies = request.get("cookies", None)
                    timeout = request.get("timeout", None)

                    authen = prepare_auth(auth)
                    req = self.build_request(url=url, method=method, headers=headers,
                                             params=params, content=content, data=data, json=json,
                                             files=files, cookies=cookies, timeout=timeout)

                    # Acquire permission from the rate limiter
                    async with limiter.throttle():
                        response_list.append(
                            await self.send(request=req, auth=authen, follow_redirects=self.follow_redirects))

        return response_list

    @staticmethod
    def extract_info_from_responses(response_list: list[dict] | dict, info_list: list):
        """
        Extracts important information from a list of responses and returns a list of dicts.
        :param info_list:
        :param response_list: List of responses
        :return: List of dicts containing relevant information
        """
        # TODO: make sure info sent back is a string / simple format and not HeaderTypes/FileTypes/etc..

        extracted_info = []

        if info_list is None:
            info_list = ["url", "status_code", "headers", "content"]

        # if response list is just one response, it's put in a list
        for response in (response_list if isinstance(response_list, list) else [response_list]):
            if info_list is not None:
                info_dict = {}
                for info in info_list:
                    info_dict[info] = response.get(info, None)
                extracted_info.append(info_dict)

        return extracted_info

    @staticmethod
    def filter_responses_by_status(response_list, target_statuses: list | int):
        if not isinstance(target_statuses, list):
            target_statuses = [target_statuses]
        # Another way to filter: response.status_code // 100 == 5 ==> all 5xx statuses
        # But you have to specify for each status type
        return [response for response in response_list if response.get("status_code") in target_statuses]

    @staticmethod
    def count_successful_responses(response_list):
        return Requester.filter_responses_by_status(response_list, 200)


class GraphQLRequester(Requester):
    default_headers = {
        "Content-Type": "application/json",
    }

    def __init__(self, baseurl, headers, auth: dict, cookies, timeout):
        super().__init__(baseurl, headers, auth, cookies, timeout)
        pass


class SOAPRequester(Requester):
    default_headers = {
        "Content-Type": "text/xml; charset=UTF-8",
        "SOAPAction": None,
    }

    # remove those 2 classes (API Type logic is made in higher parts of the engine (such as modules) )

    def __init__(self, baseurl, headers, auth: dict, cookies, timeout):
        super().__init__(baseurl, headers, auth, cookies, timeout)


##### TESTING THE REQUESTER #####
if __name__ == '__main__':

    req_lst = [
        # Unprotected routes
        {"url": "http://127.0.0.1:5000/api/unprotected", "method": "GET"},
        # Protected routes (requires authentication)
        {"url": "http://127.0.0.1:5000/api/protected", "method": "GET", "auth": ("user", "pass123")},
        # Protected routes (requires authentication)
        {"url": "http://127.0.0.1:5000/api/protected", "method": "GET", "auth": ("useurrr", "passsss")},
        # Route to get JWT token (requires authentication)
        {"url": "http://127.0.0.1:5000/api/get_jwt", "method": "GET", "auth": ("user", "pass123")},
        # Route with JWT authentication
        {"url": "http://127.0.0.1:5000/api/jwt", "method": "GET", "auth": ("user", "pass123")},
        # Route to test cookies
        {"url": "http://127.0.0.1:5000/api/cookies", "method": "GET"},
        # Route to handle form data
        {"url": "http://127.0.0.1:5000/api/form", "method": "POST", "data": {"key1": "value1", "key2": "value2"}},
        # Route to handle JSON data
        {"url": "http://127.0.0.1:5000/api/json", "method": "POST", "json": {"key1": "value1", "key2": "value2"}},
        # Route to handle XML data
        {"url": "http://127.0.0.1:5000/api/xml", "method": "POST",
         "content": "<data><key1>value1</key1><key2>value2</key2></data>"},
        # Route to handle query parameters
        {"url": "http://127.0.0.1:5000/api/query?param1=value1&param2=value2", "method": "GET"},
        # Route supporting multiple methods
        {"url": "http://127.0.0.1:5000/api/multiple", "method": "GET"},
        {"url": "http://127.0.0.1:5000/api/multiple", "method": "POST", "json": {"key1": "value1", "key2": "value2"}},
        {"url": "http://127.0.0.1:5000/api/multiple", "method": "PUT", "json": {"key1": "value1", "key2": "value2"}},
        {"url": "http://127.0.0.1:5000/api/multiple", "method": "DELETE"},
        # Route supporting PATCH method
        {"url": "http://127.0.0.1:5000/api/patch", "method": "PATCH", "json": {"key1": "value1", "key2": "value2"}},
        # Route supporting OPTIONS method
        {"url": "http://127.0.0.1:5000/api/options", "method": "OPTIONS"},
        # Route for single redirect
        {"url": "http://127.0.0.1:5000/api/redirect", "method": "GET"},
        # Route for multiple redirects
        {"url": "http://127.0.0.1:5000/api/multiple_redirects", "method": "GET"},
    ]

    reqs_auth = [
        # Request with Basic Authentication
        {
            "url": "http://127.0.0.1:5000/api/basic_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.BASIC, "credentials": {"username": "user", "password": "pass123"}}
        },
        # Request with Digest Authentication
        {
            "url": "http://127.0.0.1:5000/api/digest_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.DIGEST, "credentials": {"username": "user", "password": "pass123"}}
        },
        # Request with API Key Authentication (Headers)
        {
            "url": "http://127.0.0.1:5000/api/apikey_headers_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.APIKEY,
                     "credentials": {"location": "headers", "name": "X-API-Key", "value": "apikeyhere"}}
        },
        # Request with API Key Authentication (Params)
        {
            "url": "http://127.0.0.1:5000/api/apikey_params_auth?api_key=api-key-value",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.APIKEY,
                     "credentials": {"location": "params", "name": "X-API-Key", "value": "apikeyhere"}}
        },
        # Request with JWT Authentication (use to authenticate)
        {
            "url": "http://127.0.0.1:5000/api/jwt_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.JWT, "credentials": {
                "token_info": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6InVzZXIifQ.9oaQPcOIxv961Ls_5Ewcq5fC6L3H5Qj8x3OlwPhr6AU",
                "action": "use-jwt"}}
        },

        # Request with JWT Authentication (use to generate)
        {
            "url": "http://127.0.0.1:5000/api/jwt_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.JWT,
                     "credentials": {
                         "token_info": {"payload": {"name": "user"}, "secret": "secret", "algorithm": "HS256"},
                         "action": "generate-jwt"}}
        },

        # Request with AWS Authentication
        {
            "url": "http://127.0.0.1:5000/api/aws_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.AWS,
                     "credentials": {"access_id": "aid", "secret_key": "skey", "region": "reg", "service": "ec2"}}
        },
        # Request with NTLM Authentication
        {
            "url": "http://127.0.0.1:5000/api/ntlm_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.NTLM, "credentials": {"domain": "d", "username": "u", "password": "p"}}
        }
    ]

    r = Requester()


    async def runit(requester_client, req_list, rate_lim):

        # initialize  request / response queues
        request_queue = RequestQueue(request_builder=RequestBuilder())
        response_queue = ResponseQueue()

        await request_queue.populate(req_list)

        response_analyser = None
        m_h = ("match", {AnalysisOptions.RESP_CODE: {'code': [200, 201, 301]},
                         AnalysisOptions.LENGTH_LINES: {'max': 6, 'min': 3}})
        anlsys = [AnalysisOptions.RESP_CODE, AnalysisOptions.LENGTH_LINES, AnalysisOptions.RESP_HEADER,
                  AnalysisOptions.LENGTH_BYTES]
        response_analyser = ResponseAnalyser(match_hide=m_h, analysis=anlsys)

        rate_limiter = RateLimiter(rate_limit=rate_lim)

        print("starting worker method ")
        async with rate_limiter:
            # Acquire permission from the rate limiter
            async with rate_limiter.throttle():
                # Get the next URL from the queue
                async with request_queue:
                    while not request_queue.empty():
                        print("getting request")
                        request, auth = await request_queue.get()
                        response = await requester_client.send_request(request, auth)

                        try:
                            if response_analyser is not None:
                                analysis = response_analyser.response_analysis(response=response)
                                if analysis:
                                    print(analysis)

                            await response_queue.put(response)
                        except ResponseNotMatchedExc:
                            # If response wasn't matched it won't be added to the response queue
                            continue

                # Response queue stops loading when sending requests is over
                response_queue.is_loading = not response_queue.is_loading

        for resp in response_queue.dump():
            if resp is not None:
                print(resp.url)
                print(resp.status_code)
                print(resp.text)
                print(f"time elapsed {resp.elapsed.total_seconds()} seconds")
                print(resp.encoding)
                print("does it have redirection: ", resp.has_redirect_location)
                print("################################################################")

        """
        out = await req.send_requests(request_list=reqs_auth, rate_limiter=r_lim)
        
        for i in out:
            print(i.url)
            print(i.status_code)
            print(i.text)
            print(f"time elapsed {i.elapsed.total_seconds()} seconds")
            print(i.encoding)
            print("does it have redirection: ", i.has_redirect_location)
            print("################################################################")
            
        """


    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)

    start_time = time.time()
    event_loop.run_until_complete(runit(r, req_lst, rate_lim=3))
    event_loop.close()
    end_time = time.time() - start_time

    print("total time elapsed : ", end_time)

    # asyncio.run(runit(r, req_lst, rate_lim=100))

# TODO:

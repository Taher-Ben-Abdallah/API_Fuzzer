import asyncio
import time
from typing import Callable

from fuzzer_core.engine.queues.request_queue import RequestQueue
from fuzzer_core.engine.queues.response_queue import ResponseQueue
from fuzzer_core.engine.ratelimiter import RateLimiter
from fuzzer_core.engine.request_builder import RequestBuilder
from fuzzer_core.engine.requester.types_modes import AuthMode
from fuzzer_core.engine.requester.requester import Requester
from fuzzer_core.engine.response_analyser import ResponseNotMatchedExc


# TODO: work out a way to show requests exceeding timeout limits
class FuzzWorker:

    def __init__(self, request_queue: RequestQueue, response_queue: ResponseQueue, requester_client=None, rate_limiter=None,
                 response_analyser=None, plugin_func: Callable = None, is_paused=False):
        """

        :param is_paused:
        :param event_loop:
        :param request_queue:
        :param response_queue:
        :param requester_client:
        :param response_analyser:
        """
        super().__init__()
        self.request_queue = request_queue
        self.response_queue = response_queue

        self.requester_client = requester_client if requester_client is not None else None
        self.rate_limiter = rate_limiter if rate_limiter is not None else None
        self.response_analyser = response_analyser if response_analyser is not None else None
        self.plugin_function = plugin_func if plugin_func is not None else None
        self.is_paused = is_paused

        # self.event_loop = asyncio.new_event_loop() if event_loop is None else event_loop
        print("successfully created fuzzworker")

    async def work(self):
        print("starting work method ")

        # Check if rate limiter exists and use it if it does
        if self.rate_limiter:
            async with self.rate_limiter:
                async with self.rate_limiter.throttle():
                    await self.process_requests()
        else:
            # If no rate limiter, directly process the requests
            await self.process_requests()

    async def process_requests(self):
        # Get the next URL from the queue
        async with self.request_queue:
            print("BEFORE QUEUE EMPTY CHECK  *** QSIZE:  " + str(self.request_queue.qsize()))
            while not self.request_queue.empty():
                print("getting request")
                request, auth = await self.request_queue.get()

                if self.plugin_function:
                    responses = await self.plugin_function(requester_client=self.requester_client, request=request,
                                                           auth=auth)
                else:
                    responses = [await self.requester_client.send_request(request, auth)]

                for response in responses:
                    analysis = None
                    try:
                        if self.response_analyser is not None:
                            analysis = self.response_analyser.response_analysis(response=response)
                            if analysis:
                                print(analysis)
                        await self.response_queue.put((response, analysis))

                    except ResponseNotMatchedExc:
                        # If response wasn't matched it won't be added to the response queue
                        continue

        print("no more responses")
        # Response queue stops loading when sending requests is over
        self.response_queue.is_loading = not self.response_queue.is_loading

    '''async def work(self):
        print("starting worker method ")
        async with self.rate_limiter:
            # while True:
            # Acquire permission from the rate limiter
            async with self.rate_limiter.throttle():

                # Get the next URL from the queue
                async with self.request_queue:

                    while not self.request_queue.empty():
                        print("getting request")
                        request, auth = await self.request_queue.get()

                        if self.plugin_function:
                            responses = await self.plugin_function(requester_client=self.requester_client, request=request,
                                                                   auth=auth)
                        else:
                            responses = [await self.requester_client.send_request(request, auth)]

                        for response in responses:
                            analysis = None
                            try:
                                if self.response_analyser is not None:
                                    analysis = self.response_analyser.response_analysis(response=response)
                                    if analysis:
                                        print(analysis)
                                await self.response_queue.put((response, analysis))
                            except ResponseNotMatchedExc:
                                # If response wasn't matched it won't be added to the response queue
                                continue

                print("no more responses")
                # Response queue stops loading when sending requests is over
                self.response_queue.is_loading = not self.response_queue.is_loading
'''


##################### Testing here #######################

if __name__ == '__main__':
    # TODO:
    #  -
    #  - check how to build the requests ( on a separate thread)

    async def worker(rate_limiter, request_queue, requester_client, response_analyser, response_queue):
        print("starting worker method ")
        async with rate_limiter:
            # while True:
            # Acquire permission from the rate limiter
            async with rate_limiter.throttle():

                # Get the next URL from the queue
                async with request_queue:

                    while not request_queue.empty():
                        print("getting request")
                        request, auth = await request_queue.get()
                        response = await requester_client.send_request(request, auth)

                        analysis = None
                        if response_analyser is not None:
                            analysis = response_analyser.response_analysis(
                                response=response)

                        try:
                            if response_analyser is not None:
                                analysis = response_analyser.response_analysis(
                                    response=response)
                                if analysis:
                                    print(analysis)

                            await response_queue.put((response, analysis))
                        except ResponseNotMatchedExc:
                            # If response wasn't matched it won't be added to the response queue
                            continue

                print("no more responses")
                # Response queue stops loading when sending requests is over
                response_queue.is_loading = not response_queue.is_loading


    # This function will run in the background to populate the queue
    async def populate_queue(request_queue, req_list):
        await request_queue.populate(req_list)
        print("Request queue populated.")


    async def runit(req_list, rate_lim, conc_lim=None, threads=None):

        req = Requester()

        # initialize  request / response queues
        request_queue = RequestQueue(request_builder=RequestBuilder())
        response_queue = ResponseQueue()

        print("instantiating ratelimiter")
        r_lim = RateLimiter(rate_limit=rate_lim, concurrency_limit=conc_lim)

        # Start the queue population in the background
        populate_task = asyncio.create_task(populate_queue(request_queue, req_list))

        # Start the workers
        worker_task = asyncio.create_task(worker(
            rate_limiter=r_lim,
            request_queue=request_queue,
            requester_client=req,
            response_analyser=None,
            response_queue=response_queue
        ))

        # Wait for all tasks to complete
        await asyncio.gather(populate_task, worker_task)

        # await request_queue.populate(req_list)
        # await worker(request_queue=request_queue, response_queue=response_queue,response_analyser=None, rate_limiter=r_lim, requester_client=req)

        for req, analysis in response_queue.dump():
            if req and analysis:
                print(req.url)
                print(req.status_code)
                print(req.text)
                print(f"time elapsed {req.elapsed.total_seconds()} seconds")
                print(req.encoding)
                print("does it have redirection: ", req.has_redirect_location)
                print("################################################################")


    reqs_auth = [
        {
            "url": "http://127.0.0.1:4444/api/basic_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.BASIC, "credentials": {"username": "user", "password": "pass123"}}
        },
        # Request with Digest Authentication
        {
            "url": "http://127.0.0.1:4444/api/digest_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.DIGEST, "credentials": {"username": "user", "password": "pass123"}}
        },
        # Request with API Key Authentication (Headers)
        {
            "url": "http://127.0.0.1:4444/api/apikey_headers_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.APIKEY,
                     "credentials": {"location": "headers", "name": "X-API-Key", "value": "apikeyhere"}}
        },
        # Request with API Key Authentication (Params)
        {
            "url": "http://127.0.0.1:4444/api/apikey_params_auth?api_key=api-key-value",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.APIKEY,
                     "credentials": {"location": "params", "name": "X-API-Key", "value": "apikeyhere"}}
        },
        # Request with JWT Authentication (use to authenticate)
        {
            "url": "http://127.0.0.1:4444/api/jwt_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.JWT, "credentials": {
                "token_info": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6InVzZXIifQ.9oaQPcOIxv961Ls_5Ewcq5fC6L3H5Qj8x3OlwPhr6AU",
                "action": "use-jwt"}}
        },

        # Request with JWT Authentication (use to generate)
        {
            "url": "http://127.0.0.1:4444/api/jwt_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.JWT,
                     "credentials": {
                         "token_info": {"payload": {"name": "user"}, "secret": "secret", "algorithm": "HS256"},
                         "action": "generate-jwt"}}
        },

        # Request with AWS Authentication
        {
            "url": "http://127.0.0.1:4444/api/aws_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.AWS,
                     "credentials": {"access_id": "aid", "secret_key": "skey", "region": "reg", "service": "ec2"}}
        },
        # Request with NTLM Authentication
        {
            "url": "http://127.0.0.1:4444/api/ntlm_auth",
            "method": "GET",
            "auth": {"auth_mode": AuthMode.NTLM, "credentials": {"domain": "d", "username": "u", "password": "p"}}
        }
    ]

    req_lst = [
        # Unprotected routes
        {"url": "http://127.0.0.1:4444/api/unprotected", "method": "GET"},
        # Protected routes (requires authentication)
        {"url": "http://127.0.0.1:4444/api/protected",
         "method": "GET", "auth": ("user", "pass123")},
        # Protected routes (requires authentication)
        {"url": "http://127.0.0.1:4444/api/protected",
         "method": "GET", "auth": ("useurrr", "passsss")},
        # Route to get JWT token (requires authentication)
        {"url": "http://127.0.0.1:4444/api/get_jwt",
         "method": "GET", "auth": ("user", "pass123")},
        # Route with JWT authentication
        {"url": "http://127.0.0.1:4444/api/jwt",
         "method": "GET", "auth": ("user", "pass123")},
        # Route to test cookies
        {"url": "http://127.0.0.1:4444/api/cookies", "method": "GET"},
        # Route to handle form data
        {"url": "http://127.0.0.1:4444/api/form", "method": "POST",
         "data": {"key1": "value1", "key2": "value2"}},
        # Route to handle JSON data
        {"url": "http://127.0.0.1:4444/api/json", "method": "POST",
         "json": {"key1": "value1", "key2": "value2"}},
        # Route to handle XML data
        {"url": "http://127.0.0.1:4444/api/xml", "method": "POST",
         "content": "<data><key1>value1</key1><key2>value2</key2></data>"},
        # Route to handle query parameters
        {"url": "http://127.0.0.1:4444/api/query?param1=value1&param2=value2",
         "method": "GET"},
        # Route supporting multiple methods
        {"url": "http://127.0.0.1:4444/api/multiple", "method": "GET"},
        {"url": "http://127.0.0.1:4444/api/multiple", "method": "POST",
         "json": {"key1": "value1", "key2": "value2"}},
        {"url": "http://127.0.0.1:4444/api/multiple", "method": "PUT",
         "json": {"key1": "value1", "key2": "value2"}},
        {"url": "http://127.0.0.1:4444/api/multiple", "method": "DELETE"},
        # Route supporting PATCH method
        {"url": "http://127.0.0.1:4444/api/patch", "method": "PATCH",
         "json": {"key1": "value1", "key2": "value2"}},
        # Route supporting OPTIONS method
        {"url": "http://127.0.0.1:4444/api/options", "method": "OPTIONS"},
        # Route for single redirect
        {"url": "http://127.0.0.1:4444/api/redirect", "method": "GET"},
        # Route for multiple redirects
        {"url": "http://127.0.0.1:4444/api/multiple_redirects", "method": "GET"},
    ]

    # create async event loop
    evt_loop = asyncio.new_event_loop()

    asyncio.set_event_loop(evt_loop)

    start_time = time.time()
    # evt_loop.run_until_complete(runit(req_list=req_lst, rate_lim=50, threads=3))  ==> results in a windows event related error
    # asyncio.run_coroutine_threadsafe(runit(req_list=req_lst, rate_lim=50, threads=3), evt_loop) #==> doesn't runt

    # ==>works but there's a getter error (check debugger)
    # asyncio.run(runit(req_list=reqs_auth, rate_lim=50, conc_lim=4, threads=3))
    asyncio.run(runit(req_list=[reqs_auth[0]] * 500, rate_lim=150, threads=3))
    end_time = time.time() - start_time
    print("total time elapsed : ", end_time)

    """
        async def worker_fun(self,even):
            print("starting worker method ")
            async with rate_limiter:
                while True:
                    # Acquire permission from the rate limiter
                    async with rate_limiter.throttle():

                        # Get the next URL from the queue
                        with request_queue:
                            print("getting request")
                            request, auth = await request_queue.get()
                            response = await requester_client.send_request(request, auth)

                            if response_analyser is not None:
                                analysis = response_analyser.response_analysis(response=response)

                            # TODO: FIX THIS -> to be able to send back:
                            #  - Response (r.status_code,r.cookies,r.headers, r.elapsed, r.text)
                            #  - Analysis
                            await self.response_queue.put((response, analysis))
    """

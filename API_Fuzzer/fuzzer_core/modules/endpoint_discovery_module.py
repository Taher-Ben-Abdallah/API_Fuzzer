import asyncio

from fuzzer_core.modules.fuzz_base_module import FuzzBaseModule, create_fuzz_tuples


# TODO:
#  - generate requests (add utility that forms the requests) (done)
#  - tree search method (done)
#  - request codes based search (Next)


class EndpointDiscoveryModule(FuzzBaseModule):

    def __init__(self, wordlists: list, response_analysis, num_workers: int = 1, depth: int = None, rate_limiting=None,
                 common_fields=None, config=None):
        """

        :param depth:
        :param wordlists:
        :param response_analysis:
        :param rate_limiting:
        :param common_fields:
        :param config:
        """

        super().__init__(num_workers=num_workers, response_analysis=response_analysis, wordlists=wordlists,
                         rate_limiting=rate_limiting,
                         common_fields=common_fields, config=config)
        self.depth = depth

    def run(self, url, depth=None):
        # Should return API Spec ( REST/SOAP/GraphQL each with its wrapper will add endpoints in the convenient way)
        # Module work starts here

        fuzz_tuples = create_fuzz_tuples(
            wordlists_list=[wlist.wordlist for wlist in self.wordlists])

        api_spec = asyncio.run(self.search(
            endpoint=url, fuzz_tuples=fuzz_tuples, depth=depth if depth else self.depth))
        return api_spec

    async def search(self, endpoint, depth, fuzz_tuples):

        req_content = {"url": endpoint["url"]}

        # Generating requests on separate thread
        await asyncio.to_thread(self.generate_reqs_from_wlists, req_content, 'product', True, fuzz_tuples)

        # Start discovering API endpoints (from response queue)
        await self.run_worker()

        # TODO: if response code is correct :
        # add endpoint to API description ( dict or object (specification wrapper))

        endpoint['child_endpoints'] = []
        with self.response_queue as response_queue:
            child_endpoint = self.discover_endpoints(response_queue.get)
            if child_endpoint is not None:
                endpoint['child_endpoints'].append(child_endpoint)

        if depth > 0:
            for child in endpoint['child_endpoints']:
                child['child_endpoints'] = self.search(
                    child, depth - 1, fuzz_tuples)

        return endpoint

    def discover_endpoints(self, response):

        # TODO: this method , based on response codes (check notebook) and request methods
        # TODO: api specification instead of endpoint dictionary
        #  - add content type from response when matching a status code

        # LOGIC OF RESPONSE CODES AND METHODS

        endpoint = {}

        if response.status_code in (200, 201, 204):
            endpoint['path'] = response.url.path
            # other things to add to endpoint info

        if response.status_code == 401:
            # can try to bypass
            endpoint['path'] = response.url.path
            endpoint['requires_authentication'] = True

        if response.status_code == 403:
            # can try to bypass
            endpoint['path'] = response.url.path
            endpoint['requires_authorization'] = True

        # 405 -> method not allowed
        if response.status_code == 405:
            endpoint['path'] = response.url.path

        # 400 -> bad request (missing or malformed header/param/data)
        if response.status_code == 400:
            endpoint['path'] = response.url.path

        if response.status_code in (301, 302, 307, 308):
            # for follow_redirects, the requester will send the request to the location in the first response (will
            # not be a 3XX code)
            endpoint['path'] = response.url.path

        # other statuses ( 404,...)
        return None


async def endpoint_discovery_plugin_func(requester_client, request, auth):
    """

    :param requester_client:
    :param request:
    :param auth:
    :return:
    """
    resps = []

    # Try OPTIONS request to determine allowed methods
    request.method = "OPTIONS"
    options_resp = await requester_client.send_request(request, auth)
    resps.append(options_resp)

    if options_resp.status_code in [200, 204]:
        # Extract the allowed methods from the Allow header (split and stripped)
        allowed_methods = [s.strip()
                           for s in options_resp.headers.get('Allow', '').split(',')]

        for method in allowed_methods:
            request.method = method
            resps.append(await requester_client.send_request(request, auth))

    else:

        # Manually send different methods to the specified endpoint
        request.method = "GET"
        r = await requester_client.send_request(request, auth)
        resps.append(r)
        if r.status_code in [200, 201, 204, 401, 403]:
            for method in ["POST", "PUT", "PATCH", "DELETE"]:
                request.method = method
                resps.append(await requester_client.send_request(request, auth))

    return resps

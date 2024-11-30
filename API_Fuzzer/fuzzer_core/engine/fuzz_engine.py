from fuzzer_core.engine.response_analyser import ResponseNotMatchedExc


async def worker(self):
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
                    response = await self.requester_client.send_request(request, auth)

                    analysis = None
                    if self.response_analyser is not None:
                        analysis = self.response_analyser.response_analysis(response=response)

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

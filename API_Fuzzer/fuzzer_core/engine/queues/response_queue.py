from asyncio import Queue, QueueEmpty
#from queue import Queue, Empty as QueueEmpty


class NoMoreItems(Exception):
    def __init__(self, message="The queue has no more items in it", additional_info=None):
        self.message = message
        self.additional_info = additional_info

    def __str__(self):
        return f"{self.message}{' (' + self.additional_info + ')' if self.additional_info else ''}"


class ResponseQueue(Queue):
    """
    Contains tuples of matched response content, analysis results, flags from analysing (exple: sensitive info ...)
    """

    def __init__(self):
        super().__init__()
        self.is_loading = True
        # asyncio queues come with internal lock, no need to use locks explicitly here

    async def put(self, *responses: tuple):
        print("ResponseQueue: RESPONSE IN RESPONSE QUEUE")
        for response in responses:
            print("ResponseQueue: ", response)
            await super().put(response)
            # self.put_nowait(response)
        print("ResponseQueue: ", self.qsize())

    def put_batch(self, responses):
        for response in responses:
            self.put(response)

    async def get(self):
        while True:
            try:
                return await super().get()
                #return self.get_nowait()
            except QueueEmpty:
                if self.is_loading:
                    continue
                print("Responsequeue.get: Error: Response queue is empty. Unable to dequeue a request. Works as it should DW")
                raise NoMoreItems

    def get_noasync(self):
        while True:
            try:
                return self.get_nowait()
            except QueueEmpty:
                if self.is_loading:
                    continue
                #print("Responsequeue.get: Error: Response queue is empty. Unable to dequeue a request.")
                raise NoMoreItems

    def dump(self):
        #print(self.is_loading)
        while True:
            try:
                yield self.get_noasync()
            except NoMoreItems:
                print("Responsequeue.dump: no more items ")
                break

    def __aenter__(self):
        return self

    def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            # log error here and safely close the class
            pass
        self.close()

    def close(self):
        pass




'''
class ResponseQueue(Queue):
    """
    Contains tuples of matched response content, analysis results, flags from analyzing (e.g., sensitive info)
    """

    def __init__(self):
        super().__init__()
        self.is_loading = True

    def put(self, *responses: tuple):
        """
        Puts one or more responses into the queue.
        """
        print("ResponseQueue: RESPONSE IN RESPONSE QUEUE")
        for response in responses:
            print("ResponseQueue:", response)
            super().put(response)
        print("ResponseQueue:", self.qsize())

    def put_batch(self, responses):
        """
        Adds a batch of responses to the queue.
        """
        for response in responses:
            self.put(response)

    def get(self):
        """
        Retrieves an item from the queue without waiting if it's empty.
        If the queue is empty and no more items are loading, raises NoMoreItems.
        """
        while True:
            try:
                return super().get_nowait()
            except QueueEmpty:
                if self.is_loading:
                    continue
                print("ResponseQueue.get: Error: Response queue is empty. Unable to dequeue a response.")
                raise NoMoreItems

    def dump(self):
        """
        Yields items from the queue until it is empty.
        """
        print(self.is_loading)
        while True:
            try:
                yield self.get()
            except NoMoreItems:
                print("ResponseQueue.dump: no more items")
                break

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            # Log error here and safely close the class if needed
            pass
        self.close()

    def close(self):
        """
        Stops loading new items into the queue and clears the queue.
        """
        self.is_loading = False
        while not self.empty():
            try:
                self.get_nowait()
            except QueueEmpty:
                break
'''

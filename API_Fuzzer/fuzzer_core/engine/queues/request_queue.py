import json
from asyncio import (Queue, QueueEmpty)
#from queue import Queue, Empty as QueueEmpty
from urllib.parse import urlparse

import httpx

from fuzzer_core.engine.request_builder import RequestBuilder, RequestBuildError
from fuzzer_core.engine.requester.types_modes import HttpMethod

from httpx import _types as request_types


# TODO:
#  - Add Verification of types and contents when putting items
#  - Group the custom exceptions under one folder and file based on usage

def verify_request(request: httpx.Request):
    if request.method not in HttpMethod.__members__():
        return False

    if not isinstance(request.url, request_types.URLTypes):
        return False

    if not isinstance(request.headers, request_types.HeaderTypes):
        return False


def is_valid_url(url):
    try:
        parsed_url = urlparse(url)
        # Check if scheme or netloc is present
        if parsed_url.scheme or parsed_url.netloc:
            return True
        else:
            return False
    except ValueError:
        return False


def is_valid_json(content):
    try:
        json.loads(content)
        return True
    except ValueError:
        return False


def validate_request(request: dict):
    # check if any key has no value
    if any([field_value is None for field_key, field_value in request.items()]):
        return False
    if request["method"] not in HttpMethod.__members__:
        return False

    if not is_valid_url(request["url"]):
        return False

    if request.get("json", None):
        if not is_valid_json(request["json"]):
            return False

    if request.get("auth", None):
        if not (isinstance(request["auth"], tuple) or isinstance(request["auth"], dict)):
            return False

    return True


class NoMoreItems(Exception):
    def __init__(self, message="The queue has no more items in it", additional_info=None):
        self.message = message
        self.additional_info = additional_info

    def __str__(self):
        return f"{self.message}{' (' + self.additional_info + ')' if self.additional_info else ''}"


class RequestQueue(Queue):
    def __init__(self, request_builder: RequestBuilder):
        super().__init__()
        # asyncio queues come with internal lock, no need to use locks explicitly here

        self.request_builder = request_builder
        self.is_loading = True

    def loading_start(self):
        if not self.is_loading:
            self.is_loading = True

    def loading_stop(self):
        if self.is_loading:
            self.is_loading = False

    async def populate(self, items: list[dict]):
        """
            populates the request queue with requests objects created from items
        :param items: list of dicts
        :return:
        """
        self.loading_start()
        try:
            for item in items:
                await self.put(item)
        finally:
            self.loading_stop()

    async def put(self, item: dict):
        """
            gets request contents in a dict, builds request object and loads it in  queue
        :param item: dict of request contents
        :return:
        """

        try:
            print("RequestQueue: WE ARE PUTTING")
            print("RequestQueue: ", item)
            if validate_request(item):
                try:
                    req = self.request_builder.build_request(req_dict=item)
                    print("RequestQueue: ", req)
                    await super().put(req)
                    # self.put_nowait(req)
                    print("RequestQueue: ", self.qsize())
                except RequestBuildError as e:
                    print("RequestQueue: ERROR : ", e)

        except Exception as e:
            print(e)
            # NonValidRequest exception
            # RequestBuildError exception

    async def get(self):
        """
        Getting an item from the queue (without waiting if empty), if queue empty and no more items are getting
        loaded, it returns None
        :return: item (tuple) or None
        """
        while True:
            try:
                # return self.get_nowait()
                return await super().get()
            except QueueEmpty:
                if self.is_loading:
                    continue
                print("Error: Request queue is empty. Unable to dequeue a request.")
                raise NoMoreItems

    def get_batch(self, n):
        return [self.get() for _ in range(n)]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type:
            # exception will mostly be a NoMoreItems exception
            print(exc_value)
            # invoke close before exiting the context manager
        self.close()

    def close(self):
        self.loading_stop()
        # Clear the queue without retrieving its contents
        while not self.empty():
            self.get_nowait()





'''
class RequestQueue(Queue):
    def __init__(self, request_builder: RequestBuilder):
        super().__init__()
        self.request_builder = request_builder
        self.is_loading = True

    def loading_start(self):
        if not self.is_loading:
            self.is_loading = True

    def loading_stop(self):
        if self.is_loading:
            self.is_loading = False

    def populate(self, items: list[dict]):
        """
            Populates the request queue with request objects created from items
        :param items: list of dicts
        :return:
        """
        self.loading_start()
        try:
            for item in items:
                self.put(item)
        finally:
            self.loading_stop()

    def put(self, item: dict):
        """
            Receives request contents in a dict, builds request object, and loads it into the queue.
        :param item: dict of request contents
        :return:
        """
        try:
            print("RequestQueue: WE ARE PUTTING")
            print("RequestQueue:", item)
            if validate_request(item):
                try:
                    req = self.request_builder.build_request(req_dict=item)
                    print("RequestQueue:", req)
                    super().put(req)
                    print("RequestQueue:", self.qsize())
                except RequestBuildError as e:
                    print("RequestQueue: ERROR:", e)
        except Exception as e:
            print(e)

    def get(self):
        """
        Retrieves an item from the queue without waiting if it's empty.
        If the queue is empty and no more items are loading, raises NoMoreItems.
        :return: item (tuple) or None
        """
        while True:
            try:
                return super().get_nowait()
            except QueueEmpty:
                if self.is_loading:
                    continue
                print("Error: Request queue is empty. Unable to dequeue a request.")
                raise NoMoreItems

    def get_batch(self, n):
        return [self.get() for _ in range(n)]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            # exception will mostly be a NoMoreItems exception
            print(exc_value)
            # invoke close before exiting the context manager
        self.close()

    def close(self):
        self.loading_stop()
        # Clear the queue without retrieving its contents
        while not self.empty():
            try:
                self.get_nowait()
            except QueueEmpty:
                break

'''
"""
EXAMPLE CODE USAGE

with req_queue:
    req_queue.put(item)

with req_queue: 
    req_queue.get(item)
    
"""

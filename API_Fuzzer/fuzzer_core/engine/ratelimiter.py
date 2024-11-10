import asyncio
import math
import time
from contextlib import asynccontextmanager

"""
NOTES:

- 
- if you want to remove the concurrency limiter, then remove the semaphore code ( in init and throttle)
"""


class RateLimiter:
    def __init__(self,
                 rate_limit: int,
                 concurrency_limit: int = None) -> None:

        if not rate_limit or rate_limit < 1:
            raise ValueError('rate limit must be non zero positive number')

        # Validation on the concurrency limit if provided and creation of Semaphore to handle concurrency
        if concurrency_limit:
            if concurrency_limit < 1:
                raise ValueError('concurrent limit must be non zero positive number')
        else:
            concurrency_limit = 1
        self.semaphore = asyncio.Semaphore(concurrency_limit)

        self.rate_limit = rate_limit
        self.tokens_queue = asyncio.Queue(rate_limit)
        self.tokens_consumer_task = asyncio.create_task(self.consume_tokens())

    async def add_token(self) -> None:
        await self.tokens_queue.put(1)
        return None

    async def consume_tokens(self):
        """

        :return:
        """
        try:
            consumption_rate = 1 / self.rate_limit
            last_consumption_time = 0

            while True:
                if self.tokens_queue.empty():
                    await asyncio.sleep(consumption_rate)
                    continue

                # monotonic time is more useful in measuring time intervals
                current_consumption_time = time.monotonic()
                total_tokens = self.tokens_queue.qsize()

                time_from_last_consumption = current_consumption_time - last_consumption_time
                calculated_tokens_to_consume = math.floor(
                    time_from_last_consumption / consumption_rate)
                tokens_to_consume = min(
                    total_tokens, calculated_tokens_to_consume)

                for i in range(0, tokens_to_consume):
                    self.tokens_queue.get_nowait()

                last_consumption_time = time.monotonic()

                await asyncio.sleep(consumption_rate)
        except asyncio.CancelledError:
            # handle cancellation of the consume_tokens task if cancelled explicitly.
            # you can ignore the error here and deal with closing this task later but this is not advised
            raise
        except Exception as e:
            # do something with the error and re-raise
            raise

    @asynccontextmanager
    async def throttle(self):
        await self.semaphore.acquire()
        await self.add_token()
        try:
            yield
        finally:
            self.semaphore.release()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # log error here and safely close the class
            pass

        await self.close()

    async def close(self) -> None:
        if self.tokens_consumer_task and not self.tokens_consumer_task.cancelled():
            try:
                self.tokens_consumer_task.cancel()
                await self.tokens_consumer_task
            except asyncio.CancelledError:
                # we ignore this exception, but it is good to log and signal the task was cancelled
                pass
            except Exception as e:
                # log here and deal with the exception
                raise


"""
EXAMPLE CODE USAGE

async def worker(rate_limiter, request_queue):
    async with rate_limiter:
        while True:
            # Acquire permission from the rate limiter
            async with rate_limiter.throttle():
                # Get a request from the queue and send an asynchronous request
                request = await request_queue.get()
                if not request:
                    break
                else: 
                    await send_request()
"""

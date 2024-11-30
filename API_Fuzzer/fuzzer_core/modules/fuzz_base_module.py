import ast
import asyncio
import re
from typing import Callable

from fuzzer_core.engine.fuzzworker import FuzzWorker
from fuzzer_core.engine.queues.request_queue import RequestQueue
from fuzzer_core.engine.queues.response_queue import ResponseQueue
from fuzzer_core.engine.ratelimiter import RateLimiter
from fuzzer_core.engine.request_builder import RequestBuilder
from fuzzer_core.engine.requester.requester import Requester
from fuzzer_core.engine.response_analyser import ResponseAnalyser
from utils.wordlist_wrapper import Wordlist


# TODO: make sure you can pause fuzzing and stop it

# TODO: OTHER MODULES TO CREATE
#  - headers manipulation
#  - parameter fuzzing
#  - Body fuzzing: form data / json (REST, GraphQL) / xml
#  - auth manipulation


class FuzzBaseModule:
    def __init__(self, num_workers: int = 1, response_analysis: dict = None, wordlists: dict | list = None,
                 rate_limiting: dict = None, common_fields: dict = None, config: dict = None, proxy: str = None,
                 http_version: dict = {'v1': True, 'v2': False}):

        self.rate_limiter = None
        self.num_workers = num_workers

        self.wordlists = None if not wordlists else wordlists
        # initialize wordlist wrappers (if needed)
        # self.wordlists = []
        # if wordlists:
        #   if isinstance(wordlists, str):
        #       wordlists = [wordlists]
        #    for wordlist in wordlists:
        #        self.wordlists.append(Wordlist(wordlist))

        # initialize  request / response queues
        self.request_queue = RequestQueue(request_builder=RequestBuilder(common_fields=common_fields, config=config))
        self.response_queue = ResponseQueue()

        # initialize ratelimiter
        self.rate_limit = rate_limiting.get('rate_limit', None) if rate_limiting else None
        self.concurrency_limit = rate_limiting.get('concurrency_limit', None) if rate_limiting else None
        # if rate_limit and concurrency_limit:
        #    self.rate_limiter = RateLimiter(rate_limit=rate_limit, concurrency_limit=concurrency_limit)

        # create requester Client
        self.requester_client = Requester(proxy=proxy, http1=http_version['v1'], http2=http_version['v2'])

        # create response analyser
        self.response_analyser = None
        if response_analysis is not None:
            matching_requirements = response_analysis.get('matching_requirements', None)
            analysis_parameters = response_analysis.get('analysis_parameters', None)
            if matching_requirements or analysis_parameters:
                self.response_analyser = ResponseAnalyser(match_hide=matching_requirements,
                                                          analysis=analysis_parameters)
        print(self.response_analyser)
        self.is_paused = None

    def toggle_is_paused(self):
        self.is_paused = not self.is_paused

    async def run_workers(self, plugin_func: Callable = None):
        fuzz_worker = FuzzWorker(request_queue=self.request_queue, response_queue=self.response_queue,
                                 requester_client=self.requester_client, rate_limiter=self.rate_limiter,
                                 response_analyser=self.response_analyser, plugin_func=plugin_func)
        tasks = [fuzz_worker.work() for _ in range(self.num_workers)]
        await asyncio.gather(*tasks)
        #await fuzz_worker.work()

    async def populate_req_queue(self, req_list: list[dict]):
        await self.request_queue.populate(req_list)
        print("Request queue populated.")

    async def run_fuzz(self, req_details, iterator):
        self.is_paused = False
        if self.rate_limit is not None:
            self.rate_limiter = RateLimiter(rate_limit=self.rate_limit, concurrency_limit=self.concurrency_limit or None)
        loaded_contents = load_fuzzwords(input_param=req_details,
                                         wordlists_dict=self.wordlists,
                                         iterator=iterator)

        await self.populate_req_queue(req_list=loaded_contents)

        print("QSIZE run_fuzz: ", str(self.request_queue.qsize()))
        # Wait for all tasks to complete
        # await asyncio.gather(self.populate_req_queue(req_list=loaded_contents),self.run_workers())
        await self.run_workers()

    def base_fuzz_results(self, response: bool = False, analysis: bool = True):
        for resp, anal in self.response_queue.dump():
            yield resp if response else None, anal if analysis else None

    '''
    def generate_reqs_from_wlists(self, req_content, iterator=None, reuse_fuzz=False, fuzz_tuples=None):
        """
        Loads fuzzwords into requests and puts them into the request queue
        :param req_content:
        :param iterator:
        :param reuse_fuzz:
        :param fuzz_tuples:
        :return:
        """

        loaded_contents = load_fuzzwords(input_param=req_content,
                                         wordlists_dict=self.wordlists,
                                         iterator=iterator) \
            if reuse_fuzz else load_fuzzwords_yields(input_param=req_content,
                                                     wordlists_dict=self.wordlists,
                                                     iterator=iterator)

        for loaded in loaded_contents:
            self.request_queue.put(loaded)

    '''


#######################################
class BadInputException(Exception):
    def __init__(self):
        pass


###############################################################################################
def check_fuzz_point_matches(matches, dict_len):
    # Ensure matches are unique
    unique_matches = set(matches)
    if len(unique_matches) != len(matches):
        return False

    # Check if the number of unique matches the length of the wordlist
    if len(unique_matches) != dict_len:
        return False

    return True


def create_fuzz_tuples(wordlists_list: list[list | tuple], iterator=None) -> list:
    """
    Creates a list of tuples from a list of lists/tuples based on the passed iterator
    :param iterator: str for how to combine fuzzwords for each iteration
    :param wordlists_list: list of lists or tuples
    :return: list
    """
    match iterator:
        case 'zip':
            return Wordlist.create_zip_list(wordlists_list)
        case 'product':
            return Wordlist.create_product_list(wordlists_list)
        case None:
            return Wordlist.create_product_list(wordlists_list)


def extract_ordered_wordlists_list(input_str, wordlists_dict):
    """
    Gets wordlists dict, orders the wordlists by position in input var ,
    returns list of tuples (wordlists)
    :param input_str:
    :param wordlists_dict:
    :return:
    """
    # Create a list to store (index, key) pairs for each key found in the string
    positions = [(input_str.index(key), key) for key in wordlists_dict if key in input_str]

    # Sort the list by the index positions in the string
    positions.sort()

    # Order the dictionary by the appearance of its keys in the string
    ordered_dict = {key: wordlists_dict[key] for _, key in positions}
    print('LIST OF ORDERED WLISTS', list(ordered_dict.values()))
    return list(ordered_dict.values())


def load_fuzzwords(input_param: str | dict, wordlists_dict: dict, iterator: str = None,
                   fuzz_tuples: list[tuple] = None) -> list:
    """
    Loads fuzzwords from wordlists into the request raw string or dictionary of values
    with defined iteration of wordlist items
    :param input_param: request content raw string or dict
    :param wordlists_dict: dict of fuzzpoint value (key) and tuple of wordlist items (value)
    :param iterator: string indicating how to combine fuzzwords for each iteration
    :param fuzz_tuples: either provide fuzz tuples or will be created
    :return: list of input string or dict loaded with fuzzwords
    """

    # Define the regex pattern for the new format: $word$
    fuzz_pattern = r'\$\w+\$'

    input_var = str(input_param) if isinstance(input_param, dict) else input_param

    # Find all matches in the input string
    matches = re.findall(fuzz_pattern, input_var)

    # Check if input string is valid to load fuzz into it
    if not check_fuzz_point_matches(matches, len(wordlists_dict)):
        raise BadInputException

    # Combine fuzzwords from the wordlists into tuples
    tuples_list = fuzz_tuples if fuzz_tuples else create_fuzz_tuples(iterator=iterator,
                                                                     wordlists_list=extract_ordered_wordlists_list(
                                                                         input_str=input_var, wordlists_dict=wordlists_dict))

    vals_loaded = []
    # Replace each unique $word$ with values from the replacement lists
    for fuzzwords_tuple in tuples_list:
        replaced_string = input_var
        for i, match in enumerate(matches):
            # Replace only unique occurrences and keep track of replacements to avoid duplicates
            if match in replaced_string:
                replaced_string = replaced_string.replace(match, str(fuzzwords_tuple[i]), 1)

        if isinstance(input_param, dict):
            vals_loaded.append(ast.literal_eval(replaced_string))
        else:
            vals_loaded.append(replaced_string)
    return vals_loaded


def load_fuzzwords_yields(input_param: str | dict, wordlists_dict: dict, iterator: str = None,
                          fuzz_tuples: list[tuple] = None):
    """
    Loads fuzzwords from wordlists into the request raw string or dictionary of values
    with defined iteration of wordlist items
    :param input_param: request content raw string or dict
    :param wordlists_dict: list of lists or tuples
    :param iterator: string indicating how to combine fuzzwords for each iteration
    :param fuzz_tuples: either provide fuzz tuples or will be created
    :return: list of input string or dict loaded with fuzzwords
    """

    # Define the regex pattern for the new format: $word$
    fuzz_pattern = r'\$\w+\$'

    input_var = str(input_param) if isinstance(input_param, dict) else input_param

    # Find all matches in the input string
    matches = re.findall(fuzz_pattern, input_var)
    print("Matches found:", matches)

    # Check if input string is valid to load fuzz into it
    if not check_fuzz_point_matches(matches, len(wordlists_dict)):
        raise BadInputException

    # Combine fuzzwords from the wordlists into tuples
    tuples_list = fuzz_tuples if fuzz_tuples else create_fuzz_tuples(
        iterator=iterator, wordlists_list=extract_ordered_wordlists_list(input_str=input_var, wordlists_dict=wordlists_dict))

    # Define a generator for processing fuzzwords
    def process_fuzzwords():
        # Replace each unique $word$ with values from the replacement lists
        for fuzzwords_tuple in tuples_list:
            replaced_string = input_var
            for i, match in enumerate(matches):
                # Replace only the first occurrence of each match to avoid duplicate replacements
                if match in replaced_string:
                    replaced_string = replaced_string.replace(match, str(fuzzwords_tuple[i]), 1)

            if isinstance(input_param, dict):
                yield ast.literal_eval(replaced_string)
            else:
                yield replaced_string

    # Yield from the generator
    yield from process_fuzzwords()


if __name__ == '__main__':
    # 1. Define wordlists dict (placeholders and their possible values)
    '''wlists = {
        '$smth$': ('a', 'b', 'c'),
        '$smthnelse$': ('i', 'o', 'p')
    }'''
    wlists = {
        '$smth$': ('a',) * 10,
        '$smthnelse$': ('i',) * 100
    }

    # 2. Define rate limiting parameters
    rate_lim = {'rate_limit': 200, 'concurrency_limit': 100}

    # 3. Define request contents with placeholders
    request_contents = {
        'method': 'GET',
        'url': 'http://127.0.0.1:4444/',
        'headers': {
            'header1': 'value1',
            'header2': 'value2'
        },
        'body': 'This is a test body with $smth$ and $smthnelse$.'
    }
    response_analysis = {'matching_requirements': ['match', {'response-code': {'code': [200, 400, 403]}}],
                         'analysis_parameters': ["response-hash", "length-in-lines", "length-in-bytes", "length-in-chars",
                                                 "length-in-words"]
                         }

    # 4. Initialize FuzzBaseModule with the above parameters
    fuzz_module = FuzzBaseModule(
        num_workers=5,
        wordlists=wlists,
        rate_limiting=rate_lim,
        response_analysis=response_analysis,
        common_fields=None,  # Or pass any other common fields if necessary
        config=None  # Or pass the necessary config dict
    )

    asyncio.run(fuzz_module.run_fuzz(request_contents, None))

    for req, analysis in fuzz_module.response_queue.dump():
        if req:
            print(req.url)
            print(req.status_code)
            #print(req.text)
            print(f"time elapsed {req.elapsed.total_seconds()} seconds")
            print(req.encoding)
            print("does it have redirection: ", req.has_redirect_location)
            print("################################################################")

'''
    # Example usage:
    input_string = "$FUZZ$:$FUZ$/$FUZZ2$Z&"
    input_dict = {")'FUZZde": "value1", "key2": "78FUZZ1Z&e", "key3": "FUZZ2Z"}
    print(str(input_dict), ast.literal_eval(str(input_dict)))
    replacements_list = {'$FUZZ$': (10, 20, 30), '$FUZ$': (100, 200, 300), '$FUZZ2$': (1000, 2000, 3000)}

    start_time = time.time()

    generator = load_fuzzwords_yields(input_string, replacements_list, "product")
    for value in generator:
        print(value)

    """
    print("STRING INPUT RES: ", load_fuzzwords(input_string, replacements_list, "product"))
    #print("DICT INPUT RES: ", load_fuzzwords(input_dict, replacements_list, "product"))
    """

    end_time = time.time() - start_time
    print("total time elapsed : ", end_time)
'''

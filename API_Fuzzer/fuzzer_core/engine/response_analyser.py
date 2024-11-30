import base64
import hashlib
import re
import zlib
from collections import Counter
from datetime import timedelta
from urllib.parse import quote, unquote
import brotli

from enum import Enum

import httpx
from httpx import Response

from utils.encoding_decoding import hash_response_md5


class AnalysisOptions(Enum):
    LENGTH_WORDS = "length-in-words"
    LENGTH_CHARS = "length-in-chars"
    LENGTH_BYTES = "length-in-bytes"
    LENGTH_LINES = "length-in-lines"

    ###
    RESP_HEADER = "response-header"
    RESP_CODE = "response-code"
    RESP_ELAPSED_TIME = "response-elapsed-time"
    ###
    RESP_VALUE = "value-in-response"
    RESP_SENSITIVE_INFO = "sensitive-info"

    RESP_HASH = "response-hash"


class ResponseNotMatchedExc(Exception):
    pass


"""

flow : 
response_analysis -> invoke_match -> make_analysis
                  |        |
                  |-> invoke_analysis -> make_analysis

                  
match_hide= ("match" | "hide", { AnalysisOptions:{},AnalysisOptions:{ } })
analysis= [AnalysisOption.LENGTH_WORDS, AnalysisOption....] 

"""


class ResponseAnalyser:

    def __init__(self, match_hide: list[str, dict], analysis: list = None):
        self.matching_mode, self.matching_requirements = (None, None) if match_hide is None else match_hide
        self.analysis_parameters = None if analysis is None else analysis

    def response_analysis(self, response: httpx.Response) -> dict | None:
        """
        the method will do the request matching with the specified parameters and requirements At the same time will
        do the response analysis against the specified analysis parameters in the ResponseAnalysis instance
        :param response: response object to analyse and match
        :return: dict of analysis results or None if response not matched (if not matched, no need to check analysis)
        """

        analysis_results = {} if self.analysis_parameters is not None else None
        try:
            if self.matching_requirements:
                analysis_results.update(self.invoke_match(response=response, analysis_params=self.analysis_parameters))

            # Check if all analysis has been carried out (through matching)
            if not all(param in analysis_results for param in self.analysis_parameters):
                analysis_results = self.invoke_analysis(response=response, analysis_results=analysis_results)
        except ResponseNotMatchedExc:
            raise
        print("ANALYSIS RES    ", analysis_results)
        return analysis_results

    def invoke_match(self, response: httpx.Response, analysis_params: list = None) -> dict:
        """
        Will match the response with the specified matching requirements in the ResponseAnalyser instance
        If parameter is also in the analysis parameters it will be appended to the analysis_results
        :param response: response object to check against matching requirements
        :param analysis_params: list parameters of the analysis
        :return: dict of analysis results OR empty dict
        """

        analysis_results = {}
        analysis_params = [] if analysis_params is None else analysis_params

        try:
            for key, value in self.matching_requirements.items():

                if key in analysis_params:
                    analysis_results.update(
                        self.make_match_analysis(response=response, analysis_option=key, matching_conditions=value)
                    )
                else:
                    self.make_match_analysis(response=response, analysis_option=key, matching_conditions=value,
                                             return_result=False)

        except ResponseNotMatchedExc:
            # If response doesn't match requirements, this exception is raised to stop the running
            raise

        return analysis_results

    def invoke_analysis(self, response: httpx.Response, analysis_results) -> dict:
        """
        invokes analysis for specified parameters in the ResponseAnalyser instance and appends result to the passed
        analysis results dict
        :param response: response object to be analysed
        :param analysis_results: dict in which the analysis results will be appended
        :return: dict
        """
        for param in self.analysis_parameters:
            if param not in analysis_results.keys():
                analysis_results.update(
                    self.make_match_analysis(response=response, analysis_option=param))

        return analysis_results

    def make_match_analysis(self, response: httpx.Response, analysis_option, matching_conditions=None,
                            return_result=True) -> dict:
        """
        Analyses the given response against one of the analysis options, and tries to match it with the conditions
        specified
        result returned if return_result is True ( if you only want to match the request , set it to false)

        :param response:
        :param analysis_option:
        :param matching_conditions:
        :param return_result:
        :return: dict --> the analysis results OR empty dict
        """

        out = None

        match analysis_option:
            case AnalysisOptions.LENGTH_BYTES.value:
                out = self.calculate_length_in_bytes(response.text)

            case AnalysisOptions.LENGTH_LINES.value:
                out = self.calculate_length_in_lines(response.text)

            case AnalysisOptions.LENGTH_WORDS.value:
                out = self.calculate_length_in_words(response.text)

            case AnalysisOptions.LENGTH_CHARS.value:
                out = self.calculate_length_in_chars(response.text)

            #####
            case AnalysisOptions.RESP_CODE.value:
                if matching_conditions is not None:
                    if (self.match_response_code(response.status_code, matching_conditions.get('code', []))) != (
                            self.matching_mode != "hide"):
                        raise ResponseNotMatchedExc
                # Analysis result
                out = response.status_code

            case AnalysisOptions.RESP_ELAPSED_TIME.value:
                if matching_conditions is not None:
                    maximum = matching_conditions.get('max', None)
                    minimum = matching_conditions.get('min', None)

                    if (self.match_response_elapsed_time(response.elapsed, min_time=minimum, max_time=maximum)
                    ) != (self.matching_mode != "hide"):
                        raise ResponseNotMatchedExc
                # Analysis result
                out = response.elapsed

            case AnalysisOptions.RESP_HEADER.value:
                if matching_conditions is not None:
                    # if header matched and mode is "hide" Or if header not matched and mode is "match"
                    if (self.match_header_in_response(response=response,
                                                      headers=matching_conditions.get('headers', {}))
                    ) != (self.matching_mode != "hide"):
                        raise ResponseNotMatchedExc

                # Analysis result
                out = dict(response.headers)

            case AnalysisOptions.RESP_VALUE.value:
                if matching_conditions is not None:
                    if (
                            self.value_in_response(content=response.text,
                                                   target_value=matching_conditions.get('value'))) != (
                            self.matching_mode != "hide"):
                        raise ResponseNotMatchedExc

            case AnalysisOptions.RESP_SENSITIVE_INFO.value:
                out = self.match_sensitive_information(content=response.text)
                if matching_conditions is not None:
                    if (any(info in out for info in matching_conditions.get('info', []))) != (
                            self.matching_mode != "hide"):
                        raise ResponseNotMatchedExc

            case AnalysisOptions.RESP_HASH.value:
                out = hash_response_md5(response)

        # to avoid rewriting the same code for each method to be invoked, the matching of the analysis will be done here
        if analysis_option in [AnalysisOptions.LENGTH_BYTES.value, AnalysisOptions.LENGTH_LINES.value,
                               AnalysisOptions.LENGTH_WORDS.value,
                               AnalysisOptions.LENGTH_CHARS.value]:
            # matching response
            if matching_conditions is not None:
                maximum_len = matching_conditions.get('max', None)
                minimum_len = matching_conditions.get('min', None)
                if ((maximum_len is None or out <= maximum_len) and (minimum_len is None or out >= minimum_len)
                ) != (self.matching_mode != "hide"):
                    raise ResponseNotMatchedExc

        res = {analysis_option: out}

        return res if return_result else {}

    @staticmethod
    def calculate_length_in_bytes(content):
        """
        Calculate the length of the response in bytes.
        :param content: The response object or content
        :return: Length in bytes
        """
        if isinstance(content, str):
            return len(content.encode('utf-8'))
        elif isinstance(content, bytes):
            return len(content)
        else:
            return 0

    @staticmethod
    def calculate_length_in_chars(content):
        """
        Calculate the length of the response in characters.
        :param content: The response object or content
        :return: Length in characters
        """
        if isinstance(content, str):
            return len(content)
        elif isinstance(content, bytes):
            return len(content.decode('utf-8'))
        else:
            return 0

    @staticmethod
    def calculate_length_in_words(content):
        """
        Calculate the number of words in the response.
        :param content: The response object or content
        :return: Number of words
        """
        if isinstance(content, str):
            return len(content.split())
        elif isinstance(content, bytes):
            return len(content.decode('utf-8').split())
        else:
            return 0

    @staticmethod
    def calculate_length_in_lines(content):
        """
        Calculate the number of lines in the response.
        :param content: The response object or content
        :return: Number of lines
        """
        if isinstance(content, str):
            return len(content.splitlines())
        elif isinstance(content, bytes):
            return len(content.decode('utf-8').splitlines())
        else:
            return 0

    @staticmethod
    def search_regex_in_response(content, regex_pattern):
        """
        Search for a regex pattern in the response content.
        :param content: The response object or content
        :param regex_pattern: The regex pattern to search for
        :return: True if match or False
        """
        if isinstance(content, str):
            content = content
        elif isinstance(content, bytes):
            content = content.decode('utf-8')
        else:
            return False

        # Search for the regex pattern in the response content
        match = re.search(regex_pattern, content)

        return True if match else False

    @staticmethod
    def value_in_response(content, target_value) -> bool:
        """
        Check if a certain value is present in the response content or not .
        :param content: The response object or content
        :param target_value: The value to check for
        :return: True if the value is present (or not present, based on the state), False otherwise
        """
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        return target_value in content

    def match_response_code(self, response_code, codes: int | list[int]):
        if isinstance(codes, int):
            codes = [codes]

        return response_code in codes

    '''
    def match_response_code(self, responses: list[Response], codes: int | list[int]):
        """
            filters responses based on the response codes you're looking for
        :param responses: list of Response objects
        :param codes: one or list of response codes (int)
        :return: list of Response objects
        """
        if isinstance(codes, int):
            codes = [codes]

        return list(filter(lambda x: x.status_code in codes, responses))
    '''

    def match_response_elapsed_time(self, response_elapsed: timedelta, min_time: float = None,
                                    max_time: float = None):
        """
        Match responses based on the elapsed time.
        :param response_elapsed: List of tuples (Response objects, float)
        :param min_time: Minimum elapsed time (optional)
        :param max_time: Maximum elapsed time (optional)
        :return: List of matched responses
        """

        # Check if the elapsed time is within the specified range
        if (min_time is None or response_elapsed >= timedelta(seconds=min_time)) and \
                (max_time is None or response_elapsed <= timedelta(seconds=max_time)):
            return True
        return False

    def match_header_in_response(self, response: Response, headers: dict) -> bool:
        """
        Check if a request header is present among a list of responses.
        :param headers: headers to match with response headers
        :param response: Response object
        :return: True or False
        """

        resp_headers = {key.lower(): value for key, value in response.headers.items()}
        for key, value in headers.items():
            if key.lower() not in resp_headers:
                return False
            if value:
                if value != resp_headers[key.lower()]:
                    return False
        return True

    @staticmethod
    def match_sensitive_information(content: str):
        """
        Check if the request content contains sensitive information using regular expressions.
        :param content: The content of the request
        :return: True if sensitive information is found, False otherwise
        """
        detected_info = []
        sensitive_patterns = {
            # Credit Card Numbers
            "16 digits credit card numbers": r'\b\d{16}\b',  # 16-digit credit card numbers
            "Credit card numbers": r'\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b',  # Various credit card number formats
            "Social Security Numbers": r'\b\d{3}[ -]?\d{2}[ -]?\d{4}\b',  # Social Security Numbers with optional hyphens
            "Email Addresses": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email Addresses
            # "us_phone_number": r'\b\d{3}[ -]?\d{3}[ -]?\d{4}\b',  # US phone numbers with optional hyphens
            "International phone numbers": r'\+(?:\d{1,4}[ -]?)?(?:\d{1,}\.?)?\d{1,}(?:[ -]?\d{1,}){1,}\b',
            # International phone numbers
            "Common password patterns": r'\b(?:password|pass|pwd)[A-Za-z0-9._%+-]*[:=]?[A-Za-z0-9._%+-]+\b',
            # Common password patterns
            "API Keys": r'\b(?:api[-_]?key|access[-_]?token)[:=]?[A-Za-z0-9._%+-]+\b',  # API Keys
            "Date of birth": r'\b\d{1,2}[ /-]\d{1,2}[ /-]\d{2,4}\b',  # Date of birth with various separators
            # "Addresses": r'\b\d+\s[A-Za-z0-9._%+-]+\s[A-Za-z0-9._%+-]+\b',  # Addresses
            # "PIN codes": r'\b\d{4}\b',  # Personal Identification Numbers (PIN)
            # "URLs": r'\bhttps?://[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # URLs
        }

        for key, pattern in sensitive_patterns.items():
            if re.search(pattern, content):
                detected_info.append(key)

        return detected_info

    @staticmethod
    def extract_response_information(response: str) -> dict:
        response_information = {}

        # Extract headers and body
        header, _, body = response.partition('\r\n\r\n')
        headers = {}
        for line in header.splitlines()[1:]:  # Skip the first line (status line)
            if ': ' in line:
                key, value = line.split(': ', 1)
                headers[key.strip()] = value.strip()
        print(header, body)
        print(headers)

        # Content length in bytes
        response_information['length_in_bytes'] = ResponseAnalyser.calculate_length_in_bytes(response)
        response_information['length_in_lines'] = ResponseAnalyser.calculate_length_in_lines(response)
        response_information['length_in_words'] = ResponseAnalyser.calculate_length_in_words(response)
        response_information['length_in_chars'] = ResponseAnalyser.calculate_length_in_chars(response)

        # Sensitive information
        response_information['sensitive_information'] = ResponseAnalyser.match_sensitive_information(response)

        # Extract the most common words from the body only
        words = re.findall(r'\b\w+\b', body.lower())
        print(words)
        if words:
            response_information['most_common_words'] = Counter(words).most_common(5)
        else:
            response_information['most_common_words'] = []

        # Server Type and Version
        server_header = headers.get('Server', '').lower()
        response_information['server_info'] = {}
        if server_header:
            if "apache" in server_header:
                server_type = "Apache"
            elif "nginx" in server_header:
                server_type = "Nginx"
            elif "iis" in server_header:
                server_type = "IIS"
            else:
                server_type = "Unknown"
            server_version = re.search(r"[\d.]+", server_header)
            response_information['server_info']['type'] = server_type
            response_information['server_info']['version'] = server_version.group(0) if server_version else None

        # Authentication Information
        auth_header = headers.get('Authorization', '').lower()
        if auth_header.startswith('bearer'):
            auth_type = 'Bearer Token'
        elif auth_header.startswith('basic'):
            auth_type = 'Basic Authentication'
        elif 'set-cookie' in headers:
            auth_type = 'Session Cookie'
        else:
            auth_type = 'None detected'
        response_information['authentication'] = {'technique': auth_type}

        # Security Measures
        security_measures = []
        if 'Strict-Transport-Security' in headers:
            security_measures.append('HSTS (Strict Transport Security)')
        if 'Content-Security-Policy' in headers:
            security_measures.append('CSP (Content Security Policy)')
        if headers.get('X-Content-Type-Options', '').lower() == 'nosniff':
            security_measures.append('Content Type Sniffing Protection')
        if headers.get('X-Frame-Options', '').lower() in ['deny', 'sameorigin']:
            security_measures.append('Clickjacking Protection')
        if headers.get('X-XSS-Protection', '').startswith('1'):
            security_measures.append('XSS Protection')
        response_information['security_measures'] = security_measures

        # Rate Limiting Information
        rate_limit_info = {}
        if 'X-RateLimit-Limit' in headers:
            rate_limit_info['limit'] = headers['X-RateLimit-Limit']
        if 'X-RateLimit-Remaining' in headers:
            rate_limit_info['remaining'] = headers['X-RateLimit-Remaining']
        if 'X-RateLimit-Reset' in headers:
            rate_limit_info['reset_time'] = headers['X-RateLimit-Reset']
        response_information['rate_limiting'] = rate_limit_info

        return response_information


if __name__ == '__main__':
    # Example mock HTTP response to test the function
    mock_response = """
    HTTP/1.1 200 OK
    Server: Apache/2.4.41 (Ubuntu)
    Authorization: Bearer abcdef12345
    Set-Cookie: sessionId=xyz789; HttpOnly
    Strict-Transport-Security: max-age=31536000; includeSubDomains
    Content-Security-Policy: default-src 'self'
    X-Content-Type-Options: nosniff
    X-Frame-Options: DENY
    X-XSS-Protection: 1; mode=block
    X-RateLimit-Limit: 100
    X-RateLimit-Remaining: 75
    X-RateLimit-Reset: 1609459200
    Cache-Control: no-cache

    Hello world! Testing the response analyzer. Hello again! Password is secret."""

    # Call the function and print the results
    response_info = ResponseAnalyser.extract_response_information(mock_response)
    print(response_info)

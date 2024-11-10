import base64
import hashlib
import zlib
import brotli
import html
from urllib.parse import quote, unquote

import httpx


class EncDecException(Exception):
    def __init__(self):
        pass


def encode_content(content: str | bytes, encoding_method: str | list[str]):
    """
    Encode the content using the specified encoding method.
    Accepts chain encoding with recursive calls.
    :param content: The content to encode.
    :param encoding_method: The encoding method(s) to apply (e.g., 'base64', 'urlencode', 'md5', 'sha1', 'gzip', 'deflate', 'brotli', 'html_entities').
    :return: Encoded content.
    """
    if isinstance(encoding_method, list):
        if not encoding_method:  # Empty list, end recursion
            return content
        method = encoding_method[0]
        remaining_methods = encoding_method[1:]
    else:
        method = encoding_method
        remaining_methods = []

    # Ensure content is in the correct format for each encoding type
    if isinstance(content, str):
        content_bytes = content.encode('utf-8')
    else:
        content_bytes = content
    try:
        match method:
            case 'base64':
                encoded = base64.b64encode(content_bytes).decode('utf-8')
            case 'urlencode':
                encoded = quote(content) if isinstance(content, str) else quote(content.decode('utf-8'))
            case 'md5':
                encoded = hashlib.md5(content_bytes).hexdigest()
            case 'sha1':
                encoded = hashlib.sha1(content_bytes).hexdigest()
            case 'gzip':
                compressed = zlib.compress(content_bytes)
                encoded = base64.b64encode(compressed).decode('utf-8')
            case 'deflate':
                compressed = zlib.compress(content_bytes, zlib.DEFLATED)
                encoded = base64.b64encode(compressed).decode('utf-8')
            case 'brotli':
                compressed = brotli.compress(content_bytes)
                encoded = base64.b64encode(compressed).decode('utf-8')
            case 'html_entities':
                encoded = html.escape(content) if isinstance(content, str) else html.escape(content.decode('utf-8'))
            case _:
                encoded = content  # Unknown encoding method, return original content
    except EncDecException:
        encoded = 'Error: Encoding failed'

    return encode_content(encoded, remaining_methods) if remaining_methods else encoded


def decode_content(content: str, decoding_method: str | list[str]):
    """
    Decode the content using the specified decoding method.
    Accepts chain decoding with recursive calls.
    :param content: The content to decode.
    :param decoding_method: The decoding method(s) to apply (e.g., 'base64', 'urlencode', 'gzip', 'deflate', 'brotli', 'html_entities').
    :return: Decoded content.
    """
    if isinstance(decoding_method, list):
        if not decoding_method:  # Empty list, end recursion
            return content
        method = decoding_method[0]
        remaining_methods = decoding_method[1:]
    else:
        method = decoding_method
        remaining_methods = []

    if isinstance(content, str):
        content_bytes = content.encode('utf-8')
    else:
        content_bytes = content
    try:

        match method:
            case 'base64':
                decoded = base64.b64decode(content_bytes).decode('utf-8')
            case 'urlencode':
                decoded = unquote(content)
            case 'gzip':
                decompressed = zlib.decompress(base64.b64decode(content)).decode('utf-8')
                decoded = decompressed
            case 'deflate':
                decompressed = zlib.decompress(base64.b64decode(content), zlib.DEFLATED).decode('utf-8')
                decoded = decompressed
            case 'brotli':
                decompressed = brotli.decompress(base64.b64decode(content)).decode('utf-8')
                decoded = decompressed
            case 'html_entities':
                decoded = html.unescape(content)
            case _:
                decoded = content  # Unknown decoding method, return original content
    except EncDecException:
        decoded = 'Error: Decoding failed'

    return decode_content(decoded, remaining_methods) if remaining_methods else decoded


def hash_response_md5(response: httpx.Response):
    from fuzzer_core.engine.requester.requester import Requester

    # Convert the HTTP response to a string
    response_str = Requester.reconstruct_response(response)

    # Encode the response string to bytes and hash it
    md5_hash = hashlib.md5(response_str.encode('utf-8')).hexdigest()

    return md5_hash

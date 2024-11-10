import os

import json
import yaml
import csv
from urllib.parse import urlparse

import httpx
from httpx import RequestError


# TODO: handle exceptions raised in this module where the functions are called from


def load_string_to_dict(data_str):
    """

    :param data_str:
    :return: dict
    """
    try:
        # Try parsing as JSON
        return json.loads(data_str)
    except json.JSONDecodeError:
        try:
            # Fallback to parsing as YAML
            return yaml.safe_load(data_str)
        except yaml.YAMLError:
            raise ValueError("String is neither valid JSON nor YAML.")




def load_from_file(path: str, mode: str = None):
    """

    :param path: path to the file on the system
    :param mode: the mode with which the file should be opened (default: read text)
    :return: IO object
    :raises
    """
    try:
        if os.path.exists(path):
            raise FileNotFoundError(f'File not found: {path}')

        file_mode = 'r' if mode is None else mode
        return open(file=path, mode=file_mode)

    # raise the exception again if needed in the calling code (Optional)
    except FileNotFoundError as e:
        print(f"File not found: {e}")
        raise
    except PermissionError as e:
        print(f"Permission error: {e}")
        raise
    except Exception as e:
        print(f"Error opening file: {e}")
        raise


def load_from_url(url):
    try:
        parsed_url = urlparse(url)
        if parsed_url.scheme and parsed_url.netloc:
            response = httpx.get(url)
            response.raise_for_status()
            content = response.text

            return content

        return None
    except RequestError as err:
        print(f"Couldn't load  from url: {err}")
        raise err


def load_wordlist(wordlist_source):
    """

    :param wordlist_source:
    :return: list of words for test
    """
    try:
        content = load_from_url(wordlist_source)
        if content is not None:
            return [line.strip() for line in content.split('\n')]

        with load_from_file(path=wordlist_source) as file:
            if wordlist_source.endswith('.csv'):
                reader = csv.reader(file)
                return [row[0] for row in reader]

            return [tuple(line.split(":")) if ":" in line else line.strip() for line in file]
    except httpx.RequestError as req_err:
        print(f"Could not load wordlist from url: {wordlist_source}")
        raise
    except:
        print("Could not load wordlist from file")


def load_config_file(path):
    """

    :param path:
    :return:
    """
    with load_from_file(path) as config_file:
        if path.endswith('.json'):
            config_data = json.load(config_file)
        elif path.endswith('.yaml') or path.endswith('.yml'):
            config_data = yaml.safe_load(config_file)
            if not isinstance(config_data, dict):
                raise ValueError("Config data must be a dictionary.")
        else:
            raise ValueError("Unsupported config file format. Use JSON or YAML.")

        return config_data


def load_openapi_spec(spec_source):
    """
    Load OpenAPI specification from a file path or URL.

    :param spec_source: File path or URL to the OpenAPI specification.
    :type spec_source: str
    :return: OpenAPI specification content as a dictionary.
    :rtype: dict
    :raises FileNotFoundError: If the specified file path is not found.
    :raises requests.RequestException: If there is an issue fetching content from a URL.
    :raises json.JSONDecodeError: If the content cannot be decoded as JSON.
    :raises yaml.YAMLError: If the content cannot be parsed as YAML.
    """

    try:

        content = load_from_url(spec_source)
        if content is None:
            with load_from_file(spec_source) as file:
                content = file.read()

        try:
            return json.loads(content)
        except json.JSONDecodeError as json_error:
            try:
                return yaml.safe_load(content)
            except yaml.YAMLError as yaml_error:
                raise yaml_error

    except FileNotFoundError as file_not_found:
        raise file_not_found
    except RequestError as request_error:
        raise request_error
    except (json.JSONDecodeError, yaml.YAMLError) as decode_error:
        print("Accepted types are Json or Yaml")
        raise decode_error
    except Exception as e:
        raise Exception(f"Error loading OpenAPI specification: {e}")

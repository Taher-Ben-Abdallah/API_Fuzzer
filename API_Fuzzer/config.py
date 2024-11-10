import json
from typing import Dict, Any

import yaml

from utils.loaders import load_config_file, load_from_url

params_list = ["threads", "timeout", "wordlist", "rules"]

# Expected configuration template for validation
config_template = {
    'request': {
        'base_url': str,
        'headers': dict,
        'cookies': dict,
        'params': dict
    },
    'analysis': list,
    'match_hide': list,
    'fuzz_engine': {
        'workers': int,
        'timeout': int,
        'rate_limit': int,
        'concurrency_limit': int,
    },
    'fuzz_generator': {

    },
    'proxy': str,
    'timeout': float | int,

}


class Config(dict):
    """
        "request": {
            "headers": {"Host": "localhost","User-Agent": "Mozilla/5.0 (Macintosh)",...},
            "params": {"param1": "value1", "param2": "value2"},
            ...
        }
    """

    default_config = {
        "request": {
            "headers": {"User-Agent": "Mozilla/5.0 (Mac)"}
        },
        "fuzz_engine": {
            "workers": 4,
        },
    }

    def __init__(self, path=None, url=None):
        super().__init__()

        if not any((path, url)):
            self.load_defaults()
        try:
            if path:
                self.load_config(path=path)
            if url:
                self.load_config(url=url)
        except ValueError:
            self.load_defaults()

    def load(self, config_data):
        self.update(config_data)

    def update_from_args(self, args):
        for key, value in vars(args).items():
            if value is not None:
                self[key] = value

    def load_defaults(self):

        # TODO: make the function load the file contents into the config dict ( wordlists, rules , requests )
        self.update(self.default_config)

    def load_config(self, conf_content=None, url=None, path=None):
        """Load configuration data from a string, URL, or file path."""
        # Ensure only one of the parameters is provided
        params = [conf_content, url, path]
        if sum(p is not None for p in params) != 1:
            raise ValueError("Only one of 'conf_content', 'URL', or 'path' should be provided.")

        # Load from the provided source
        if conf_content:
            content = conf_content
        elif url:
            content = load_from_url(url)
        elif path:
            content = load_config_file(path)
        else:
            raise ValueError("A source for configuration (conf_content, URL, or path) must be provided.")

        # Attempt to parse as JSON, then YAML if JSON fails
        try:
            config_data = json.loads(content)
        except json.JSONDecodeError:
            try:
                config_data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ValueError(f"Error parsing content as JSON or YAML: {e}")

        # Validate config structure against the template
        try:
            self.validate_config(config_data, config_template)
        except ValueError:
            config_data = {}

        self.load(config_data)

    def validate_config(self, config_data: Dict[str, Any], template: Dict[str, Any], parent_key='root') -> None:
        """Validate that config_data only contains keys matching the template structure and types."""
        for key, value in config_data.items():
            # Check if the key exists in the template
            if key not in template:
                raise ValueError(f"Unexpected configuration key found: '{parent_key}.{key}'")

            expected_type = template[key]

            # Nested dictionary case
            if isinstance(expected_type, dict):
                if not isinstance(value, dict):
                    raise ValueError(f"Incorrect type for '{parent_key}.{key}': Expected dict, got {type(value).__name__}")
                # Recursively validate nested dictionaries
                self.validate_config(value, expected_type, f"{parent_key}.{key}")

            # Basic type case
            elif not isinstance(value, expected_type):
                raise ValueError(
                    f"Incorrect type for '{parent_key}.{key}': Expected {expected_type.__name__}, got {type(value).__name__}")


if __name__ == "__main__":

    # Sample JSON configuration content (conforming to config_template)
    json_conf_content = json.dumps({
        "request": {
            "headers": [{"Host": "localhost"}, {"User-Agent": "Mozilla/5.0 (Macintosh)"}],
            "cookies": [{"session_id": "12345"}]
        },
        "analysis": ["length_in_bytes", "length_in_words"],
        "match_hide": ["regex_pattern_1", "regex_pattern_2"],
        "fuzz_engine": {
            "workers": 6,
            "timeout": 20
        }
    })

    # Sample YAML configuration content (conforming to config_template)
    yaml_conf_content = """
    request:
        headers:
            - Host: "localhost"
            - User-Agent: "Mozilla/5.0 (Macintosh)"
        cookies:
            - session_id: "12345"
    analysis:
        - length_in_bytes
        - length_in_words
    match_hide:
        - regex_pattern_1
        - regex_pattern_2
    fuzz_engine:
        workers: 4
        timeout: 20
    """


    # Function to run the test with either JSON or YAML content
    def test_load_config(conf_content, is_yaml=False):
        config = Config()
        print("Testing configuration load...\n")

        try:
            config.load_config(conf_content=conf_content)
            print("Loaded configuration:", config)
        except ValueError as e:
            print(f"Error: {e}")


    # Run the test for JSON content
    print("Testing with JSON configuration:")
    test_load_config(json_conf_content)

    # Run the test for YAML content
    print("\nTesting with YAML configuration:")
    test_load_config(yaml_conf_content)

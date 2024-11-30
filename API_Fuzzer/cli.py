import argparse
import json
import threading
from argparse import ArgumentTypeError

from config import Config

import wfuzz


def parse_arguments():
    parser = argparse.ArgumentParser(description="API Fuzzing Tool -- Help")

    parser.add_argument(
        "url",
        metavar="<url to parse>",
        type=str,
        nargs=1,
        help="url to parse"
    )

    parser.add_argument(
        "-s",
        "--api_spec",
        metavar="</path/to/spec_file> OR <link to specification>",
        type=str,
        help="Path to the API specification file (e.g., OpenAPI or Swagger).",
    )

    parser.add_argument(
        '-w',
        '--wordlist',
        metavar='<wordlist>',
        type=argparse.FileType('r'),
        help='Specify your chosen wordlist after the -w flag.',
        nargs=1,
        # required=True
    )

    parser.add_argument(
        "-c",
        "--config",
        metavar="/path/to/config_file",
        type=str,
        nargs=1,
        help="Path to the fuzzer configuration file (JSON format).",
    )

    parser.add_argument(
        '-a',
        "--architecture",
        choices=['REST', 'SOAP', 'GraphQL'],
        default="REST",
        help="Specify the architecture of the API to fuzz",
        nargs=1,
    )

    parser.add_argument(
        '--report-dir',
        metavar='</path/to/report_dir>',
        type=str,
        help='Add report storage directory path.'

    )

    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        # default=1,
        help="Number of concurrent threads to use while fuzzing.",
    )

    parser.add_argument(
        "-r",
        "--rate",
        type=int,
        default=10,
        help="Rate limit for requests per second.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Request timeout in seconds.",
    )

    parser.add_argument(
        "--headers",
        help="Custom headers. Example: header1:test1,header2:test2,header3:test3",
    )

    parser.add_argument(
        "--jwt",
        type=str,
        help="JWT session header. i.e Authorization: Bearer <jwt token>",
    )

    parser.add_argument(
        "--cookies",
        help="Session cookies",
    )


    parser.add_argument(
        "-m",
        "--modules",
        type=str,
        nargs="*",
        help="List of module names to run. If not provided, all modules will be run. Example: BigIntegerDetector,IntegerOverflowDetector",
    )

    parser.add_argument(
        "--match-string",
        type=str,
        nargs="+",
        help='Match a specific string within the response text. Example: \"Operation successful\",\"User added\"',
    )

    parser.add_argument(
        "-p",
        "--proxy",
        type=str,
        help="Define a HTTP/HTTPS proxy server for requests.",
    )
    return parser.parse_args()



def main():
    args = parse_arguments()

    # Load configuration
    config = Config()
    if args.config:
        with open(args.config, "r") as config_file:
            config_data = json.load(config_file)
            config.load(config_data)

    # Update configuration with CLI arguments
    config.update_from_args(args)

    # Initialize Fuzzer instance
    fuzzer = Fuzzer(config)

    # Run the fuzzer and interactive mode in separate threads
    fuzz_thread = threading.Thread(target=fuzzer.start)
    interactive_thread = threading.Thread(target=fuzzer.interactive_mode, args=(fuzzer,))

    fuzz_thread.start()
    interactive_thread.start()

    fuzz_thread.join()
    interactive_thread.join()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import argparse
from wsgiref.simple_server import make_server

from kommunpoet.kommunpoet import Kommunpoet
from kommunpoet.wsgi import Application


def fetch_links(args):
    print("Fetching all links")
    Kommunpoet().fetch_links()


def fetch(args):
    print("Fetching data")
    Kommunpoet().fetch_data(args.force)


def compile(args):
    print("Compiling")
    Kommunpoet().compile(args.force)


def test_server(args):
    print("Listening on port 8000")
    httpd = make_server("localhost", 8000, Application)
    while True:
        try:
            httpd.handle_request()
        except Exception:
            return


def random(args):
    kommun = Kommunpoet().get_random_kommun()
    print(f"{kommun.name}\n")
    print(kommun.get_poem(chaos=args.chaos))


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    subparsers.add_parser("fetch-links", help="Fetch all links").set_defaults(func=fetch_links)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch HTML")
    fetch_parser.add_argument("--force", action="store_true", help="Fetch all data even if there is data present")
    fetch_parser.set_defaults(func=fetch)

    compile_parser = subparsers.add_parser("compile", help="Compile fetched HTML")
    compile_parser.add_argument("--force", action="store_true", help="Compile even where compilation has been done")
    compile_parser.set_defaults(func=compile)

    subparsers.add_parser("test-server", help="Fire up a test server on port 8000").set_defaults(func=test_server)

    random_parser = subparsers.add_parser("random", help="Output random poem")
    random_parser.add_argument("--chaos", action="store_true", help="Chaoz mode")
    random_parser.set_defaults(func=random)

    args = parser.parse_args()

    if "func" not in args:
        parser.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    main()

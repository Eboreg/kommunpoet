#!/usr/bin/env python3

import argparse
from wsgiref.simple_server import make_server

from kommunpoet.kommunpoet import Kommunpoet
from kommunpoet.wsgi import application


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-links", action="store_true", help="Fetch links")
    parser.add_argument("--fetch", action="store_true", help="Fetch HTML")
    parser.add_argument("--compile", action="store_true", help="Compile fetched HTML")
    parser.add_argument("--test-server", action="store_true", help="Fire up a test server")
    parser.add_argument("--random", action="store_true", help="Output random poem")
    parser.add_argument("--force", action="store_true", help="Force whatever you want to do")

    args = parser.parse_args()
    kp = Kommunpoet()

    if args.fetch_links:
        print("Fetching all links")
        kp.fetch_links()
    if args.fetch:
        print("Fetching data")
        kp.fetch_data(args.force)
    if args.compile:
        print("Compiling")
        kp.compile(args.force)
    if args.random:
        kommun = kp.random_kommun
        print(f"{kommun.name}\n")
        print(kommun.poem)
    if args.test_server:
        print("Listening on port 8000")
        httpd = make_server("localhost", 8000, application)
        httpd.handle_request()


if __name__ == "__main__":
    main()

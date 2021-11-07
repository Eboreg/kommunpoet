#!/usr/bin/env python3

import argparse
from wsgiref.simple_server import make_server

from kommunpoet.kommunpoet import Kommunpoet
from kommunpoet.wsgi import application


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--fetch", action="store_true", help="Fetch HTML")
    parser.add_argument("-c", "--compile", action="store_true", help="Compile fetched HTML")
    parser.add_argument("-t", "--test-server", action="store_true", help="Fire up a test server")

    args = parser.parse_args()
    kp = Kommunpoet()

    if args.fetch:
        print("Fetching data")
        kp.fetch_data()
    if args.compile:
        print("Compiling")
        kp.compile()
    if args.test_server:
        print("Listening on port 8000")
        httpd = make_server("localhost", 8000, application)
        httpd.handle_request()


if __name__ == "__main__":
    main()

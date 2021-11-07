from typing import Optional
from urllib.parse import parse_qs

from jinja2 import Environment, PackageLoader, select_autoescape

from kommunpoet.kommunpoet import Kommunpoet

kp = Kommunpoet()


def get_html(kommun_id=None) -> str:
    jinja = Environment(loader=PackageLoader("kommunpoet", "templates"), autoescape=select_autoescape(["html"]))
    template = jinja.get_template("index.html")
    kommun_name, poem = kp.get_name_and_poem(kommun_id)
    return template.render(choices=kp.choices, kommun_id=kommun_id, kommun_name=kommun_name, poem=poem)


def application(environ, start_response):
    # http://wsgi.tutorial.codepoint.net/application-interface
    # https://www.toptal.com/python/pythons-wsgi-server-application-interface

    if environ.get("REQUEST_METHOD").upper() == "HEAD":
        start_response("200 OK", [])
        return []

    qs = parse_qs(environ["QUERY_STRING"])
    kommun_id: Optional[str]

    if "id" in qs:
        kommun_id = qs["id"][0]
    else:
        kommun_id = None

    html = get_html(kommun_id)
    response_headers = [
        ("Content-Type", "text/html"),
        ("Content-Length", str(len(html))),
    ]

    start_response("200 OK", response_headers)
    return [html.encode("utf-8")]

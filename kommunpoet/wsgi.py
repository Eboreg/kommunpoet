import random
import sys
from typing import Optional
from urllib.parse import parse_qs, urlencode

from jinja2 import Environment, PackageLoader, select_autoescape

from kommunpoet.kommunpoet import Kommunpoet

kp = Kommunpoet()


def get_html(seed: int, directlink: str, kommun_id=None, chaos=False) -> str:
    jinja = Environment(loader=PackageLoader("kommunpoet", "templates"), autoescape=select_autoescape(["html"]))
    template = jinja.get_template("index.html")

    kommun_name, poem = kp.get_name_and_poem(id=kommun_id, chaos=chaos, seed=seed)
    return template.render(
        choices=kp.choices,
        kommun_id=kommun_id,
        kommun_name=kommun_name,
        poem=poem,
        chaos=chaos,
        directlink=directlink,
        title_name=kommun_name if kommun_id else None
    )


def application(environ, start_response):
    # http://wsgi.tutorial.codepoint.net/application-interface
    # https://www.toptal.com/python/pythons-wsgi-server-application-interface

    if environ.get("REQUEST_METHOD").upper() == "HEAD":
        start_response("200 OK", [])
        return []

    qs = parse_qs(environ["QUERY_STRING"])

    try:
        seed = int(qs["seed"][0])
    except (ValueError, IndexError, KeyError):
        seed = random.randint(1, sys.maxsize)

    qs.update(seed=[str(seed)])
    directlink = environ.get("wsgi.url_scheme") + "://" + environ.get("SERVER_NAME")
    port = environ.get("SERVER_PORT", "80")
    if port != "80":
        directlink += ":" + port
    if environ.get("SERVER_NAME") == "huseli.us":  # yes, ugly as hell
        directlink += "/kommunpoet"
    directlink += "/?" + urlencode(qs, doseq=True)

    print(environ)

    kommun_id: Optional[str]
    if "id" in qs:
        kommun_id = qs["id"][0]
    else:
        kommun_id = None

    html = get_html(seed=seed, directlink=directlink, kommun_id=kommun_id, chaos="chaos" in qs)
    response_headers = [
        ("Content-Type", "text/html"),
        ("Content-Length", str(len(html))),
    ]

    start_response("200 OK", response_headers)
    return [html.encode("utf-8")]

import random
import sys
from typing import Optional
from urllib.parse import parse_qs, urlencode, urljoin

from jinja2 import Environment, PackageLoader, select_autoescape

from kommunpoet.kommunpoet import Kommunpoet

kp = Kommunpoet()


def get_html(**context) -> str:
    jinja = Environment(loader=PackageLoader("kommunpoet", "templates"), autoescape=select_autoescape(["html"]))
    template = jinja.get_template("index.html")

    return template.render(context)


def application(environ, start_response):
    # http://wsgi.tutorial.codepoint.net/application-interface
    # https://www.toptal.com/python/pythons-wsgi-server-application-interface

    if environ.get("REQUEST_METHOD").upper() == "HEAD":
        start_response("200 OK", [])
        return []

    qs = parse_qs(environ["QUERY_STRING"])
    path = environ.get("REQUEST_URI", "").split("?")[0]

    try:
        seed = int(qs["seed"][0])
    except (ValueError, IndexError, KeyError):
        seed = random.randint(1, sys.maxsize)
        qs.update(chaos=["true"], seed=[str(seed)])
        response_headers = [
            ("Location", path + "?" + urlencode(qs, doseq=True)),
        ]
        start_response("302 Found", response_headers)
        return [b""]

    host = environ.get("wsgi.url_scheme") + "://" + environ.get("SERVER_NAME")
    port = environ.get("SERVER_PORT", "80")
    if port != "80":
        host += ":" + port

    qs.update(seed=[str(seed)])
    directlink = urljoin(host, path) + "?" + urlencode(qs, doseq=True)

    kommun_id: Optional[str]
    if "id" in qs:
        kommun_id = qs["id"][0]
    else:
        kommun_id = None

    chaos = "chaos" in qs

    kommun_name, poem = kp.get_name_and_poem(id=kommun_id, chaos=chaos, seed=seed)
    html = get_html(
        title_name=kommun_name if kommun_id else None,
        choices=kp.choices,
        kommun_id=kommun_id,
        chaos=chaos,
        kommun_name=kommun_name,
        poem=poem,
        directlink=directlink,
    )

    response_headers = [
        ("Content-Type", "text/html"),
        ("Content-Length", str(len(html))),
    ]

    start_response("200 OK", response_headers)
    return [html.encode("utf-8")]

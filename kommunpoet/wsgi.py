import random
import sys
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlencode, urljoin

from jinja2 import Environment, PackageLoader, select_autoescape

from kommunpoet.kommunpoet import Kommun, Kommunpoet

kp = Kommunpoet()


class Application:
    seed: Optional[int]

    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        self.qs = parse_qs(environ["QUERY_STRING"])
        self.path = environ.get("REQUEST_URI", "").split("?")[0]
        self.chaos = "chaos" in self.qs
        self.kommun_id = self.qs["id"][0] if "id" in self.qs else None
        self.error = None

        try:
            self.seed = int(self.qs["seed"][0])
        except (ValueError, IndexError, KeyError):
            self.seed = None

        self.status, self.headers, self.body = self.get_response()

    def __iter__(self):
        self.start_response(self.status, self.headers)
        yield self.body

    def get_context(self) -> dict:
        kommun = self.get_kommun()
        poem = kommun.get_poem(seed=self.seed, chaos=self.chaos)

        return dict(
            kommun_id=self.kommun_id,
            chaos=self.chaos,
            directlink=self.get_link(kommun.id),
            choices=kp.choices,
            kommun_name=kommun.name,
            poem=poem,
            error=self.error,
        )

    def get_html(self, context: dict) -> str:
        jinja = Environment(loader=PackageLoader("kommunpoet", "templates"), autoescape=select_autoescape(["html"]))
        template = jinja.get_template("index.html")
        return template.render(context)

    def get_kommun(self) -> Kommun:
        kommun = None
        if self.kommun_id:
            kommun = kp.get_kommun_by_id(self.kommun_id)
            if kommun is None:
                self.error = f"Hittade inte kommunen {self.kommun_id}. ;( Här får du en slumpmässig kommun istället."
        if kommun is None:
            kommun = kp.get_random_kommun(self.seed)
        return kommun

    def get_link(self, kommun_id: str) -> str:
        host = self.environ.get("wsgi.url_scheme") + "://" + self.environ.get("SERVER_NAME")
        port = self.environ.get("SERVER_PORT", "80")
        if port != "80":
            host += ":" + port
        qs = self.qs.copy()
        qs.update(id=[kommun_id], seed=[str(self.seed)])
        return urljoin(host, self.path) + "?" + urlencode(qs, doseq=True)

    def get_redirect(self) -> Tuple[str, list, bytes]:
        random.seed()
        qs = self.qs.copy()
        qs.update(seed=[str(random.randint(1, sys.maxsize))])
        if not self.environ["QUERY_STRING"]:
            # No query at all = fresh load = set chaoz by default
            qs.update(chaos=["true"])
        headers = [
            ("Location", self.path + "?" + urlencode(qs, doseq=True)),
        ]
        return "302 Found", headers, b""

    def get_response(self) -> Tuple[str, list, bytes]:
        if self.environ.get("REQUEST_METHOD").upper() == "HEAD":
            return "200 OK", [], b""
        if "favicon.ico" in self.environ.get("PATH_INFO", ""):
            return "404 Not Found", [], b""
        if self.seed is None:
            return self.get_redirect()
        html = self.get_html(self.get_context())
        headers = [
            ("Content-Type", "text/html"),
            ("Content-Length", str(len(html))),
        ]
        return "200 OK", headers, html.encode("utf-8")

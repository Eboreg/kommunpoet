import locale
import random
import re
import shelve
import unicodedata
from typing import List, Optional, Tuple
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup


locale.setlocale(locale.LC_COLLATE, "sv_SE.UTF-8")


def split_sentence(sentence: str) -> List[str]:
    # Treat thousand-separated numbers as one word
    # Also digit + space + "%"
    new_sentence = ""
    for idx, char in enumerate(sentence):
        if char == " " and \
                idx > 0 and len(sentence) > idx + 1 and \
                sentence[idx - 1].isdigit() and \
                (sentence[idx + 1].isdigit() or sentence[idx + 1] == "%"):
            new_sentence += "<NOBREAK>"
        else:
            new_sentence += char
    words = new_sentence.split()
    words = [w.replace("<NOBREAK>", " ") for w in words]
    return words


class Kommun:
    id: str  # "Huddinge_kommun"
    name: str  # "Huddinge kommun" (no underscore)
    html: List[bytes]
    sections: List[List[str]]

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
        self.html = []
        self.sections = []

    def __eq__(self, other):
        return other.__class__ == self.__class__ and other.id == self.id

    def __lt__(self, other):
        return locale.strxfrm(self.name) < locale.strxfrm(other.name)

    def __repr__(self):
        return self.name

    @property
    def is_compiled(self) -> bool:
        return len(self.sections) > 0

    @property
    def is_fetched(self) -> bool:
        return len(self.html) > 0

    @property
    def poem(self) -> str:
        return "\n".join(self.generate_poem()).strip()

    def compile(self):
        self.sections = []
        for html in self.html:
            self.sections.extend(self.compile_one(html))

    def compile_one(self, html: bytes) -> List[List[str]]:
        # Look for contingent <p> paragraphs
        # Generates list of list of strings, where each item in inner list is
        # the contents of a <p> tag
        subsections = []  # list of strings
        sections = []  # list of subsections

        soup = BeautifulSoup(html, "html.parser")

        for child in soup.select_one(".mw-parser-output").contents:
            if child.name == "p":
                for sup in child.find_all("sup"):
                    sup.extract()
                text = unicodedata.normalize("NFKC", child.text)
                text = text.replace("\n", " ")
                text = re.sub(r"[()]*", "", text)
                text = text.strip().lower()
                subsections.append(text)
            elif subsections:
                sections.append(subsections)
                subsections = []

        # Skip all sections with total < 100 chars
        sections = [
            s for s in sections
            if sum([len(ss) for ss in s]) >= 100
        ]

        # Prefer longer sections; preferably 400+ chars
        for length in range(400, 199, -100):
            selections = [
                s for s in sections
                if sum([len(ss) for ss in s]) >= length
            ]
            if len(selections) >= 10:
                sections = selections
                break

        return sections

    def fetch(self):
        self.html = []
        response = requests.get(f"https://sv.wikipedia.org/wiki/{self.id}")
        self.html.append(response.content)
        soup = BeautifulSoup(response.content, "html.parser")
        try:
            for tr in soup.select_one("table.infobox").find_all("tr"):
                if tr.find("th", string="Centralort"):
                    href = tr.select_one("td>a")["href"]
                    response = requests.get(urljoin("https://sv.wikipedia.org/", href))
                    self.html.append(response.content)
                    break
        except Exception as e:
            print(f"*** Could not get 'Centralort' page for {self.name}: {e}")

    def generate_poem(self, poem=None, sections=None) -> List[str]:
        if self.id == "Tranemo_kommun":
            return [
                "tranemo har redan",
                "en kommunpoet",
                "",
                "så de får",
                "ingenting",
                "av mig",
                "",
                "sorry"
            ]
        poem = poem or []
        sections = sections or self.sections
        section_idx = random.randint(0, len(sections) - 1)
        for subsection in sections[section_idx]:
            sentences = re.split(r"[.?!:,] ", subsection)
            sentences = [s.strip(".?!:, ") for s in sentences]
            for sentence in sentences:
                if sentence == "blasonering":
                    continue
                if len(poem) >= 10:
                    break
                words = split_sentence(sentence)
                if len(words) > 7:
                    while words:
                        end_idx = random.randint(3, 7)
                        if end_idx == len(words) - 1:
                            end_idx = len(words)
                        poem.append(" ".join(words[:end_idx]).strip(".?!:, "))
                        words = words[end_idx:]
                else:
                    poem.append(" ".join(words))
        while len(poem) < 10:
            sections = sections[:section_idx] + sections[section_idx + 1:]
            if not sections:
                break
            poem = self.generate_poem(poem + [""], sections)
        return poem


class Kommunpoet:
    db_name = "database"
    # kommuner: Dict[str, Kommun]  # str = id
    kommuner: List[Kommun]  # str = id

    def __init__(self):
        with shelve.open(self.db_name, "c") as db:
            self.kommuner = db.get("kommuner") or []
        if not self.kommuner:
            self.fetch_links()

    @property
    def choices(self):
        yield ("", "SLUMPMÄSSIG KOMMUN")
        for kommun in sorted(self.kommuner):
            yield (kommun.id, kommun.name)

    @property
    def random_kommun(self) -> Kommun:
        return random.choice(self.kommuner)

    def compile(self, all=False):
        """If all=False, only compile those in need of compiling"""
        try:
            for kommun in self.kommuner:
                if all or not kommun.is_compiled:
                    print(f"Compiling {kommun}")
                    kommun.compile()
        finally:
            self.sync_db()

    def fetch_data(self, all=False):
        """If all=False, only fetch those in need of fetching"""
        try:
            for kommun in self.kommuner:
                if all or not kommun.is_fetched:
                    print(f"Fetching data for {kommun}")
                    kommun.fetch()
        finally:
            self.sync_db()

    def fetch_links(self):
        response = requests.get("https://sv.wikipedia.org/wiki/Lista_över_Sveriges_kommuner")
        soup = BeautifulSoup(response.content, "html.parser")
        for link in soup.select_one("table.wikitable").select("td:nth-child(2) a"):
            id = unquote(link["href"].strip("/wiki/"))
            if self.get_kommun_by_id(id) is None:
                self.kommuner.append(Kommun(id, link.text))
        self.sync_db()

    def get_kommun_by_id(self, id: str) -> Optional[Kommun]:
        for kommun in self.kommuner:
            if kommun.id == unquote(id):
                return kommun
        return None

    def get_name_and_poem(self, id: Optional[str]) -> Tuple[str, str]:
        if id is not None:
            kommun = self.get_kommun_by_id(id)
            if kommun is None:
                return f"Hittade inte kommunen {id}. ;(", ""
        else:
            kommun = self.random_kommun
        return kommun.name, kommun.poem

    def sync_db(self):
        with shelve.open(self.db_name, "n") as db:
            db["kommuner"] = self.kommuner

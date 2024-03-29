import locale
import random
import re
import shelve
import unicodedata
from copy import deepcopy
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup

from kommunpoet.markov import SeededText

locale.setlocale(locale.LC_COLLATE, "sv_SE.UTF-8")

breakwords = (
    "en", "ett", "och", "på", "i", "till", "som", "av", "efter", "från", "för",
    "genom", "hos", "om", "vid", "med", "under", "har", "eller", "att", "samt",
    "men"
)

idioms = [
    "i och med",
    "från och med",
    "till och med",
]


def split_sentence_into_rows(sentence: str) -> List[str]:
    sentence = sentence.lower()
    # 1. Make certain idioms non-breakable
    for idiom in idioms:
        sentence = sentence.replace(idiom, idiom.replace(" ", "<NOBREAK>"))
    # 2. Split paranthesised phrases to new rows
    rows = []
    while True:
        match = re.search(r"\(.*?\)", sentence)
        if not match:
            if sentence:
                rows.append(sentence)
            break
        rows.extend([sentence[:match.start()].strip(), match.group().strip("()")])
        sentence = sentence[match.end():].strip()
    # 3. Split at comma, colon, and semicolon
    new_rows: List[str] = []
    for row in rows:
        new_rows.extend(re.split(r"[;:,] ", row))
    rows = new_rows
    # 4. New row at "breakwords", but only if there are enough words before
    # and after them
    new_rows = []
    for row in rows:
        words = row.split(" ")
        new_words: List[str] = []
        for idx, word in enumerate(words):
            if word in breakwords and len(new_words) > 3 and len(words) - idx >= 3:
                new_rows.append(" ".join(new_words))
                new_words = []
            new_words.append(word)
        new_rows.append(" ".join(new_words))
    rows = [row.replace("<NOBREAK>", " ").strip(" .;:!?") for row in new_rows]
    rows = [re.sub(r" {2,}", " ", row) for row in rows]
    rows = [row for row in rows if row]
    return rows


class Kommun:
    id: str  # "Huddinge_kommun"
    name: str  # "Huddinge kommun" (no underscore)
    markov: Dict[str, Any]  # to be fed to SeededText.from_dict()
    sections: List[List[str]]

    def __init__(
            self, id: str, name: str, sections: Optional[List[List[str]]] = None,
            markov: Optional[Dict[str, Any]] = None):
        self.id = id
        self.name = name
        self.markov = markov or {}
        self.sections = sections or []

    def __eq__(self, other):
        return other.__class__ == self.__class__ and other.id == self.id

    def __lt__(self, other):
        return locale.strxfrm(self.name) < locale.strxfrm(other.name)

    def __repr__(self):
        return self.name

    @classmethod
    def clone(cls, other):
        return cls(
            id=deepcopy(other.id),
            name=deepcopy(other.name),
            sections=deepcopy(other.sections),
            markov=deepcopy(other.markov)
        )

    @property
    def filtered_sections(self) -> List[List[str]]:
        """Filter away short sections"""
        # Skip all sections with total < 100 chars
        sections = [
            s for s in self.sections
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

    @property
    def is_compiled(self) -> bool:
        return len(self.sections) > 0 and len(self.markov) > 0

    def compile(self, html_list: List[bytes]):
        self.sections = []
        for html in html_list:
            self.sections.extend(self.compile_one(html))
        self.markov = SeededText(self.flatten_sections()).compile().to_dict()

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
                text = re.sub(r" *\* *", " ", text)
                # Special case: "Kungl. Maj:t"
                text = re.sub(r"(kungl)\.", r"\1", text, flags=re.IGNORECASE)
                text = text.strip()
                subsections.append(text)
            elif subsections:
                sections.append(subsections)
                subsections = []
        return sections

    def fetch(self) -> List[bytes]:
        html = []
        response = requests.get(f"https://sv.wikipedia.org/wiki/{self.id}")
        html.append(response.content)
        soup = BeautifulSoup(response.content, "html.parser")
        try:
            for tr in soup.select_one("table.infobox").find_all("tr"):
                if tr.find("th", string="Centralort"):
                    href = tr.select_one("td>a")["href"]
                    response = requests.get(urljoin("https://sv.wikipedia.org/", href))
                    html.append(response.content)
                    break
        except Exception as e:
            print(f"*** Could not get 'Centralort' page for {self.name}: {e}")
        return html

    def flatten_sections(self, sections: Optional[List[List[str]]] = None) -> str:
        sections = sections or self.sections
        return " ".join([" ".join(s) for s in sections])

    def generate_poem(self, poem=None, sections=None, chaos=False, seed=None) -> List[str]:
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

        if chaos:
            sections = sections or self.sections
            model = SeededText.from_dict(self.markov, seed=seed)
            sentences = []
            while len(poem) < 10:
                sentence = model.make_sentence(tries=100)
                sentence = re.sub(r"(källa|källor|blasonering): ", "", sentence, flags=re.IGNORECASE)
                if sentence and sentence not in sentences:
                    poem.extend(split_sentence_into_rows(sentence) + [""])
                    sentences.append(sentence)

        else:
            sections = sections or self.filtered_sections
            if seed:
                random.seed(seed)
            section_idx = random.randint(0, len(sections) - 1)
            for subsection in sections[section_idx]:
                sentences = re.split(r"[.?!] ", subsection)
                for sentence in sentences:
                    if sentence.startswith("blasonering"):
                        continue
                    if len(poem) >= 10:
                        break
                    poem.extend(split_sentence_into_rows(sentence))
            while len(poem) < 10:
                sections = sections[:section_idx] + sections[section_idx + 1:]
                if not sections:
                    break
                poem = self.generate_poem(seed=seed, poem=poem + [""], sections=sections)

        return poem

    def get_poem(self, seed=None, chaos=False) -> str:
        return "\n".join(self.generate_poem(seed=seed, chaos=chaos)).strip()


class Kommunpoet:
    db_name = "database"
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

    def compile(self, all=False):
        """
        If all=False, only compile those in need of compiling

        In order to minimize memory usage, we don't store the html as an
        object attribute anywhere.
        """
        with shelve.open(self.db_name, "c") as db:
            html_dict = db.get("html") or {}
        try:
            for kommun in self.kommuner:
                if all or not kommun.is_compiled:
                    html_list = html_dict.get(kommun.id)
                    if not html_list:
                        print(f"*** No HTML found for {kommun} - fetch needed! ***")
                    else:
                        print(f"Compiling {kommun}")
                        kommun.compile(html_list)
        finally:
            self.sync_db()

    def fetch_data(self, all=False):
        """
        If all=False, only fetch those in need of fetching.

        In order to minimize memory usage, we don't store the html as an
        object attribute anywhere.
        """
        with shelve.open(self.db_name, "c") as db:
            html_dict = db.get("html") or {}
            try:
                for kommun in self.kommuner:
                    if all or kommun.id not in html_dict:
                        print(f"Fetching data for {kommun}")
                        html_dict[kommun.id] = kommun.fetch()
            finally:
                db["html"] = html_dict

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

    def get_random_kommun(self, seed=None) -> Kommun:
        if seed:
            random.seed(seed)
        return random.choice(self.kommuner)

    def sync_db(self):
        with shelve.open(self.db_name, "c") as db:
            db["kommuner"] = self.kommuner

    def migrate_html(self):
        # TODO: remove after migration
        with shelve.open(self.db_name, "c") as db:
            html_dict = db.get("html") or {}
        kommuner = []
        for kommun in self.kommuner:
            print(kommun)
            html_dict[kommun.id] = kommun.html
            kommuner.append(Kommun.clone(kommun))
        with shelve.open(self.db_name, "n") as db:
            db["html"] = html_dict
            db["kommuner"] = kommuner

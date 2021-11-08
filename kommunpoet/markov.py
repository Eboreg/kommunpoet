import json
import random

from markovify.chain import Chain
from markovify.text import Text


class SeededChain(Chain):
    def __init__(self, corpus, state_size, model=None, seed=None):
        self.seed = seed
        super().__init__(corpus, state_size, model)

    def move(self, state):
        if self.seed:
            self.update_seed()
            random.seed(self.seed)
        return super().move(state)

    def update_seed(self):
        if self.seed:
            if self.seed > 1_000_000_000:
                self.seed /= 2
            else:
                self.seed *= 3

    @classmethod
    def from_json(cls, json_thing, seed=None):
        obj = json.loads(json_thing) if isinstance(json_thing, str) else json_thing

        if isinstance(obj, list):
            rehydrated = {tuple(item[0]): item[1] for item in obj}
        elif isinstance(obj, dict):
            rehydrated = obj
        else:
            raise ValueError("Object should be dict or list")

        state_size = len(list(rehydrated.keys())[0])

        inst = cls(None, state_size, rehydrated, seed)
        return inst


class SeededText(Text):
    def make_sentence(self, init_state=None, **kwargs):
        if isinstance(self.chain, SeededChain):
            self.chain.update_seed()
        return super().make_sentence(init_state=init_state, **kwargs)

    def test_sentence_output(self, words, max_overlap_ratio, max_overlap_total):
        result = super().test_sentence_output(words, max_overlap_ratio, max_overlap_total)
        if not result and isinstance(self.chain, SeededChain):
            self.chain.update_seed()
        return result

    @classmethod
    def from_dict(cls, obj, seed=None, **kwargs):
        return cls(
            None,
            state_size=obj["state_size"],
            chain=SeededChain.from_json(obj["chain"], seed),
            parsed_sentences=obj.get("parsed_sentences"),
        )

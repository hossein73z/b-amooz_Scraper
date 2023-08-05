import json


class Word:
    class MeaningData:
        class Meaning:

            def __init__(self, primary: str = None, secondary: str = None):
                self.primary = primary
                self.secondary = secondary

        def __init__(self,
                     meaning: Meaning = None,
                     examples: dict = None,
                     notes: list[dict] = None
                     ):
            self.meaning = meaning
            self.examples = examples
            self.notes = notes if notes else []

    def __init__(self,
                 role: str = None,
                 deutsch: str = None,
                 plural: str = None,
                 conjugation_url: str = None,
                 tags: list[str] = None,
                 meaning_data: list[MeaningData] = None,
                 extra: dict = None
                 ):
        self.role = role
        self.deutsch = deutsch
        self.plural = plural
        self.conjugation_url = conjugation_url
        self.tags = tags if tags else []
        self.meaning_data = meaning_data if meaning_data else []
        self.extra = extra

    def to_json(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

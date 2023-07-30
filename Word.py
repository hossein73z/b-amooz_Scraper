class Word:
    class MeaningData:
        class Meaning:

            def __init__(self, primary: str = None, secondary: str = None):
                self.primary = primary
                self.secondary = secondary

        def __init__(self,
                    meaning: dict = None,
                    examples: dict = None,
                    notes: list[dict] = None
                    ):
            self.meaning = self.Meaning(**meaning)
            self.examples = examples
            self.notes = notes

    def __init__(self,
                 role: str = None,
                 deutsch: str = None,
                 tags: list[str] = None,
                 meaning_data: list[dict] = None,
                 extra: dict = None
                 ):
        self.role = role
        self.deutsch = deutsch
        self.tags = tags
        self.meaning_data = [self.MeaningData(**meaning_dict) for meaning_dict in meaning_data]
        self.extra = extra

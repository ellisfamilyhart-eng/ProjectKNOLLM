class ConceptIdentity:

    def __init__(self):
        self.aliases={}


    def add_alias(self, concept, alias):

        self.aliases[alias.lower()] = concept.lower()


    def resolve(self, word):

        word=word.lower()

        return self.aliases.get(
            word,
            word
        )
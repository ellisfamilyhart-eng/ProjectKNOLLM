import time
import random


class Cortex:

    def __init__(self, jarvix=None):
        self.jarvix = jarvix

        # temporary conscious space
        self.memory = {
            "concepts": {},
            "thoughts": [],
            "hypotheses": [],
            "confidence": {}
        }

        self.running = True
        self.depth = 0
        self.max_depth = 20


    # ---------------------------
    # receive information
    # ---------------------------

    def perceive(self, text):

        words = text.lower().replace(".", "").split()

        for w in words:
            self.activate(w)

        self.think()


    # ---------------------------
    # neuron activation
    # ---------------------------

    def activate(self, concept, amount=1):

        self.memory["concepts"][concept] = (
            self.memory["concepts"].get(concept,0)
            + amount
        )


    # ---------------------------
    # recursive thinking
    # ---------------------------

    def think(self):

        if self.depth >= self.max_depth:
            return

        self.depth += 1


        concepts = sorted(
            self.memory["concepts"],
            key=self.memory["concepts"].get,
            reverse=True
        )


        if not concepts:
            return


        idea = self.connect(concepts)


        if idea:

            self.memory["thoughts"].append(idea)

            confidence = random.random()

            self.memory["hypotheses"].append(
                {
                    "idea":idea,
                    "confidence":confidence
                }
            )


            # ask main brain
            if self.jarvix:

                answer = self.jarvix.query(idea)

                if answer:
                    self.activate(answer,0.5)



        # recursive loop

        self.think()



    # ---------------------------
    # create associations
    # ---------------------------

    def connect(self, concepts):

        if len(concepts)<2:
            return None

        return (
            concepts[0]
            +" may relate to "
            +concepts[1]
        )



    # ---------------------------
    # cleanup temporary memory
    # ---------------------------

    def clear(self):

        self.memory={
            "concepts":{},
            "thoughts":[],
            "hypotheses":[],
            "confidence":{}
        }

        self.depth=0



    def report(self):

        return self.memory



# ---------------------------
# Example
# ---------------------------

if __name__=="__main__":


    brain=Cortex()


    brain.perceive(
        "The candle is low because the meal was cooked a long time ago"
    )


    print(
        brain.report()
    )
"""
Jarvix NoLLM v7
Executive Controller V2

The decision layer.

Responsibilities:

- Receive ParseResult
- Generate thoughts
- Rank thoughts
- Decide which subsystem handles the request
- Execute the correct action

The controller does NOT:
- parse language
- generate final responses
- store memory directly
"""

from typing import Optional


class ExecutiveControllerV2:


    def __init__(
        self,
        thought_engine,
        planner=None,
        reasoner=None,
        memory=None,
        response_generator=None
    ):

        self.thought_engine = thought_engine

        self.planner = planner

        self.reasoner = reasoner

        self.memory = memory

        self.response_generator = response_generator


        self.last_thoughts = []

        self.last_action = None



    ############################################################
    # Main decision pipeline
    ############################################################


    def process(self, parse_result):


        # 1. Create internal thoughts

        thoughts = self.thought_engine.think(
            parse_result
        )


        self.last_thoughts = thoughts



        # 2. Select strongest thought

        thought = self.thought_engine.highest_priority()



        if not thought:

            return self.fallback()



        # 3. Decide action

        action = self.choose_action(
            thought
        )


        self.last_action = action



        # 4. Execute

        return self.execute(
            action,
            parse_result
        )



    ############################################################
    # Action selection
    ############################################################


    def choose_action(self, thought):


        source = thought.source



        if source == "learning":

            return "TEACH"



        if source == "reasoning":

            return "REASON"



        if source == "conversation":

            return "CONVERSATION"



        if source == "math":

            return "MATH"



        return "RESPOND"




    ############################################################
    # Execute chosen action
    ############################################################


    def execute(
        self,
        action,
        parse_result
    ):


        if action == "REASON":

            return self.reason(parse_result)



        if action == "TEACH":

            return self.teach(parse_result)



        if action == "CONVERSATION":

            return self.conversation(parse_result)



        if action == "MATH":

            return self.math(parse_result)



        return self.respond(parse_result)



    ############################################################
    # Reasoning
    ############################################################


    def reason(self, parse_result):


        if not self.planner:

            return "I need a reasoning system."



        plans = self.planner.plan_and_execute(
            parse_result
        )


        if plans:

            return str(plans[0])


        return "I could not find an answer."



    ############################################################
    # Teaching
    ############################################################


    def teach(self, parse_result):


        if self.memory:

            self.memory.add_fact(
                parse_result.subject,
                parse_result.object,
                confidence=parse_result.confidence
            )


        return "I have learned that."



    ############################################################
    # Conversation
    ############################################################


    def conversation(self, parse_result):


        return (
            "I understand. "
            "Tell me more."
        )



    ############################################################
    # Math placeholder
    ############################################################


    def math(self, parse_result):


        return (
            "Math processing is not connected yet."
        )



    ############################################################
    # Response fallback
    ############################################################


    def respond(self, parse_result):


        return (
            "I am processing what you said."
        )



    def fallback(self):

        return (
            "I am not sure how to handle that yet."
        )
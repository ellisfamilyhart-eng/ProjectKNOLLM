"""
Jarvix Cognitive Planner

Turns reasoning decisions into actions.

Different from knowledge Planner.
"""


class CognitivePlanner:


    def create_plan(self, thought):

        if thought.goal == "LOOKUP":

            return [
                "search_memory",
                "evaluate_facts",
                "generate_answer"
            ]


        if thought.goal == "STORE_FACT":

            return [
                "validate_fact",
                "check_conflicts",
                "store_memory"
            ]


        if thought.goal == "UPDATE_FACT":

            return [
                "find_existing_fact",
                "replace_or_merge",
                "store_memory"
            ]


        if thought.goal == "GREET":

            return [
                "create_social_response"
            ]


        if thought.goal == "EMPATHIZE":

            return [
                "detect_emotion",
                "create_supportive_response"
            ]


        return [
            "understand",
            "respond"
        ]
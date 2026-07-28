"""
Jarvix Memory Linker v1

Creates relationships between memories.
"""


from typing import List

from .memory_models import Memory



class MemoryLinker:



    def __init__(self):

        pass



    def similarity(
        self,
        a: Memory,
        b: Memory
    ) -> float:

        """
        Basic similarity check.

        Later this becomes embeddings.
        """

        text_a = str(
            a.content
        ).lower()


        text_b = str(
            b.content
        ).lower()



        words_a = set(
            text_a.split()
        )

        words_b = set(
            text_b.split()
        )


        if not words_a or not words_b:

            return 0



        overlap = words_a.intersection(
            words_b
        )


        return len(overlap) / max(
            len(words_a),
            len(words_b)
        )





    def link(
        self,
        memory: Memory,
        memories: List[Memory]
    ):

        """
        Find related memories
        and create connections.
        """


        for other in memories:


            # Ignore itself

            if other.id == memory.id:

                continue



            score = self.similarity(
                memory,
                other
            )



            if score >= 0.25:


                if other.id not in memory.links:

                    memory.links.append(
                        other.id
                    )


                if memory.id not in other.links:

                    other.links.append(
                        memory.id
                    )



    def get_connections(
        self,
        memory: Memory,
        memories: List[Memory]
    ):


        connected = []


        for item in memories:

            if item.id in memory.links:

                connected.append(item)



        return connected
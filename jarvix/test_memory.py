from jarvix.memory import MemoryManager



brain = MemoryManager()



brain.learn(
    "My favourite colour is blue"
)


brain.learn(
    "Python is a programming language"
)


brain.learn(
    "I fixed the parser bug by escaping regex"
)



print(
    brain.stats()
)



memories = brain.recall(
    "Python"
)


for memory in memories:

    print(
        memory.content,
        memory.memory_type,
        memory.confidence
    )
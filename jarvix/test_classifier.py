from jarvix.memory import MemoryClassifier


classifier = MemoryClassifier()



tests = [

    "My favourite colour is blue",

    "Python is a programming language",

    "I fixed the parser bug by escaping regex",

    "I am building Jarvix MemoryManager",

    "hello there"

]


for item in tests:

    result = classifier.classify(item)

    print(
        item,
        "=>",
        result.to_dict()
    )
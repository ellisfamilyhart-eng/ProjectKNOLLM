#!/bin/bash

# CuriousMind English Teaching Script
# This file contains the curl commands to teach English to CuriousMind

echo "Teaching CuriousMind English Basics..."
echo "======================================="

# Array of English language concepts
facts=(
    "English: is the most spoken language globally"
    "Grammar: is the system of rules for using language"
    "Noun: is a word that names a person, place, or thing"
    "Verb: is a word that describes an action or state"
    "Adjective: is a word that describes or modifies a noun"
    "Adverb: is a word that modifies a verb, adjective, or another adverb"
    "Pronoun: is a word that replaces a noun"
    "Preposition: is a word that shows the relationship between words"
    "Conjunction: is a word that connects words or clauses"
    "Sentence: is a complete thought with a subject and verb"
    "Subject: is who or what the sentence is about"
    "Predicate: is what the subject does or is"
    "Object: is the noun that receives the action of the verb"
    "Article: is a small word that precedes a noun (a, an, the)"
    "Tense: is the time of an action (past, present, future)"
    "Singular: means one"
    "Plural: means more than one"
    "Vowel: is a, e, i, o, u"
    "Consonant: is any letter that is not a vowel"
    "Punctuation: marks sentences"
    "Synonym: is a word with the same meaning as another word"
    "Antonym: is a word with the opposite meaning"
    "Vocabulary: is the collection of words in a language"
    "Definition: is the meaning of a word"
    "Context: is the words around a word that help explain its meaning"
    "Abstract: means not physical"
    "Concrete: means physical and tangible"
    "Character: is a person in a story"
    "Plot: is the sequence of events in a story"
    "Setting: is the place and time of a story"
    "Theme: is the main idea or message of a story"
    "Conflict: is a problem or struggle in a story"
    "Resolution: is how the conflict is solved"
    "Fiction: is a made-up story"
    "Non-fiction: is a true story based on facts"
    "Author: is the person who writes"
    "Tone: is the attitude of the writer toward the subject"
    "Mood: is the feeling created in the reader"
    "Style: is the unique way a writer writes"
    "Spelling: is putting letters in the correct order"
    "Capitalization: is using uppercase letters at the start of sentences"
    "Brainstorm: is creating many ideas quickly"
    "Outline: is a plan for writing"
    "Draft: is the first version of writing"
    "Revision: is improving writing"
    "Edit: is correcting errors in writing"
    "Literacy: is the ability to read and write"
    "Comprehension: is understanding what you read"
    "Summary: is a short version of the main ideas"
    "Quote: is the exact words from a text"
    "Persuade: is to convince someone to believe something"
    "Inform: is to give information"
    "Entertain: is to amuse or engage"
    "Describe: is to explain what something is like"
    "Compare: is to show how things are alike"
    "Analyze: is to break something into parts"
)

# Teach each fact
for fact in "${facts[@]}"; do
    curl -s -X POST http://localhost:5000/api/chat \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$fact\"}" > /dev/null
    echo "✓ Taught: $fact"
    sleep 0.1
done

echo ""
echo "Teaching complete!"
echo "Check stats at: http://localhost:5000/api/stats"

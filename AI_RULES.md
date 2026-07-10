# Jarvix NoLLM — AI Rules & Tech Stack Guidelines

This document outlines the technical stack, architectural constraints, and library usage rules for maintaining and extending the **Jarvix NoLLM** cognitive AI application.

---

## 🚀 Tech Stack Overview

* **Backend Framework**: Python 3 with **Flask** as the lightweight web server to handle REST API endpoints and serve the single-page interface.
* **Frontend Interface**: Single-page application built with **Vanilla HTML5, CSS3, and JavaScript (ES6)** embedded directly in `templates/index.html` for real-time chat, statistics, and web crawler visualization.
* **Cognitive Architecture**: A custom, multi-layered **NoLLM (No Large Language Model)** cognitive pipeline including symbolic reasoning, a directed knowledge graph, and a custom single-layer perceptron (`TinyBrain`) for pattern learning.
* **Web Scraping & Crawling**: **Requests** and **BeautifulSoup4** (with `lxml` or `html.parser`) for fetching, cleaning, and extracting structured SVO (Subject-Verb-Object) triples from web pages.
* **Data Persistence**: Flat **JSON files** (`jarvix_v2_memory.json`, `_graph.json`, `_semantic.json`) for storing facts, episodic conversations, neural weights, and vocabulary.
* **Containerization**: **Docker** and **Docker Compose** for consistent, isolated local and production deployments.

---

## 📐 Core Rules & Library Constraints

### 1. Absolutely No LLMs
* **Rule**: Do not import or use any Large Language Model APIs (OpenAI, Anthropic, Cohere, etc.) or local heavy model frameworks (Hugging Face Transformers, llama.cpp, PyTorch, TensorFlow).
* **Reason**: Jarvix is designed to run entirely on lightweight, explainable, symbolic, and custom neural-symbolic algorithms with a memory footprint under 10KB.

### 2. Web Scraping & Crawling
* **Allowed Libraries**: Use `requests` for HTTP fetching and `BeautifulSoup` (from `bs4`) for HTML parsing and DOM cleaning.
* **Prohibited**: Do not introduce heavy headless browsers (like Selenium, Playwright, or Puppeteer) unless explicitly requested, to keep the Docker image lightweight and fast.

### 3. NLP & Text Parsing
* **Rule**: Use Python's built-in `re` (Regular Expressions) module and custom rule-based heuristics for SVO (Subject-Verb-Object) extraction, intent classification, and text normalization.
* **Prohibited**: Avoid adding heavy NLP libraries like `nltk` or `spacy` unless rule-based parsing becomes completely unmaintainable.

### 4. Neural & Mathematical Operations
* **Rule**: Use Python's built-in `math` module for sigmoid activations, derivatives, and basic calculations. Use `collections` (such as `defaultdict`, `deque`, and `Counter`) for frequency tracking and Markov chains.
* **Prohibited**: Do not install `numpy`, `scipy`, or `scikit-learn` for the neural learner; keep the custom single-layer perceptron (`TinyBrain`) dependency-free.

### 5. Data Persistence
* **Rule**: Use Python's built-in `json` library for all memory serialization and deserialization. Ensure all data is saved periodically and loaded automatically on startup.
"""
Jarvix - Web Crawler Module v2
Improved HTML filtering: strips nav/ads/menus/dictionary-metadata.
Only keeps headings + main prose content.
"""

import re
import time
from urllib.parse import urlparse, urljoin
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class PageResult:
    url:            str
    title:          str  = ""
    word_count:     int  = 0
    sentence_count: int  = 0
    facts_extracted:int  = 0
    facts_stored:   int  = 0
    facts_skipped:  int  = 0
    top_topics:     list = field(default_factory=list)
    error:          str  = ""
    fetch_time_ms:  int  = 0


@dataclass
class CrawlReport:
    seed_url:       str
    pages_visited:  int   = 0
    pages_failed:   int   = 0
    total_words:    int   = 0
    total_sentences:int   = 0
    total_facts:    int   = 0
    stored_facts:   int   = 0
    duplicate_facts:int   = 0
    top_topics:     list  = field(default_factory=list)
    top_facts:      list  = field(default_factory=list)
    page_results:   list  = field(default_factory=list)
    knowledge_gain: float = 0.0
    errors:         list  = field(default_factory=list)
    elapsed_ms:     int   = 0


class WebCrawler:
    """
    Fetches web pages, strips noise, extracts factual sentences,
    stores SVO triples, and returns a structured evaluation report.
    """

    # Tags always discarded (navigation, ads, UI chrome)
    DISCARD_TAGS = {
        "script", "style", "nav", "header", "footer", "aside",
        "form", "noscript", "iframe", "svg", "button", "input",
        "select", "textarea", "meta", "link", "figure", "figcaption",
        "picture", "video", "audio", "canvas", "map", "object",
        # dictionary / wiki sidebar noise
        "table", "sup", "sub", "cite",
    }

    # CSS class / id patterns that indicate nav/ad/menu content
    NOISE_PATTERNS = re.compile(
        r"(nav|menu|sidebar|banner|ad|ads|advertisement|cookie|"
        r"popup|modal|footer|header|breadcrumb|pagination|"
        r"related|share|social|comment|login|signup|subscribe|"
        r"toc|contents|infobox|hatnote|catlinks|reflist|"
        r"references|external.links|see.also)",
        re.I
    )

    # Sentence quality filters
    _JUNK_PATTERNS = [
        re.compile(r"^\s*[\[\(].*[\]\)]\s*$"),           # [edit] (1)
        re.compile(r"^[^a-zA-Z]*$"),                      # no letters
        re.compile(r"^\s*\d+\s*$"),                       # bare numbers
        re.compile(r"(click here|read more|learn more|"   # CTA phrases
                   r"sign up|log in|subscribe|cookie|"
                   r"privacy policy|terms of)", re.I),
        re.compile(r"^.{1,10}$"),                          # too short
        re.compile(r"^.{400,}$"),                          # too long
        re.compile(r"\|.*\|"),                             # nav pipe separators
        re.compile(r"^\s*(home|about|contact|help|search"
                   r"|menu|navigation)\s*$", re.I),        # single nav words
        # Dictionary-specific noise
        re.compile(r"^(before|after|used|when|"
                   r"consonant sound|vowel sound)\s+", re.I),
        re.compile(r"\b(IPA|pronunciation|phonetic|"
                   r"syllable|hyphenation)\b", re.I),
    ]

    # Relation patterns
    _REL_PATTERNS = [
        (re.compile(r"^(.+?)\s+is\s+an?\s+(.+)$",   re.I), "is_a"),
        (re.compile(r"^(.+?)\s+are\s+an?\s+(.+)$",  re.I), "is_a"),
        (re.compile(r"^(.+?)\s+is\s+(.+)$",         re.I), "has_property"),
        (re.compile(r"^(.+?)\s+are\s+(.+)$",        re.I), "has_property"),
        (re.compile(r"^(.+?)\s+has\s+(.+)$",        re.I), "has"),
        (re.compile(r"^(.+?)\s+have\s+(.+)$",       re.I), "has"),
        (re.compile(r"^(.+?)\s+can\s+(.+)$",        re.I), "can"),
        (re.compile(r"^(.+?)\s+causes?\s+(.+)$",    re.I), "causes"),
        (re.compile(r"^(.+?)\s+contains?\s+(.+)$",  re.I), "has"),
        (re.compile(r"^(.+?)\s+includes?\s+(.+)$",  re.I), "has"),
        (re.compile(r"^(.+?)\s+refers?\s+to\s+(.+)$", re.I), "related_to"),
        (re.compile(r"^(.+?)\s+was\s+(.+)$",        re.I), "has_property"),
        (re.compile(r"^(.+?)\s+were\s+(.+)$",       re.I), "has_property"),
        (re.compile(r"^(.+?)\s+orbits?\s+(.+)$",    re.I), "related_to"),
        (re.compile(r"^(.+?)\s+(?:stores?|holds?)\s+(.+)$", re.I), "has"),
        (re.compile(r"^(.+?)\s+(?:produces?|creates?|generates?)\s+(.+)$", re.I), "causes"),
    ]

    def __init__(self, agent, max_depth=1, max_pages=10,
                 timeout_s=8, same_domain_only=True):
        self.agent            = agent
        self.max_depth        = max_depth
        self.max_pages        = max_pages
        self.timeout_s        = timeout_s
        self.same_domain_only = same_domain_only
        self._visited: set    = set()

    # ================================================================
    # PUBLIC
    # ================================================================

    def crawl(self, seed_url: str) -> CrawlReport:
        import time as _t
        t0           = _t.time()
        report       = CrawlReport(seed_url=seed_url)
        seed_domain  = urlparse(seed_url).netloc
        facts_before = self._count_facts()
        queue        = [(seed_url, 0)]
        self._visited.clear()

        while queue and (report.pages_visited + report.pages_failed) < self.max_pages:
            url, depth = queue.pop(0)
            if url in self._visited:
                continue
            self._visited.add(url)

            page = self._process_page(url)
            report.page_results.append(page)

            if page.error:
                report.pages_failed += 1
                report.errors.append(f"{url}: {page.error}")
                continue

            report.pages_visited   += 1
            report.total_words     += page.word_count
            report.total_sentences += page.sentence_count
            report.total_facts     += page.facts_extracted
            report.stored_facts    += page.facts_stored
            report.duplicate_facts += page.facts_skipped

            if depth < self.max_depth:
                for link in self._extract_links(url, seed_domain)[:5]:
                    if link not in self._visited:
                        queue.append((link, depth + 1))

        report.elapsed_ms    = int((_t.time() - t0) * 1000)
        facts_after          = self._count_facts()
        report.knowledge_gain = (facts_after - facts_before) / max(facts_before, 1) * 100
        report.top_topics    = self._top_topics(report)
        report.top_facts     = self._top_facts(report)
        return report

    # ================================================================
    # PAGE PROCESSING
    # ================================================================

    def _process_page(self, url: str) -> PageResult:
        import time as _t
        t0   = _t.time()
        page = PageResult(url=url)
        try:
            html, status = self._fetch(url)
            if not html:
                page.error = f"HTTP {status} / empty"
                return page

            title, text   = self._parse_html(html)
            page.title    = title
            sentences     = self._split_sentences(text)
            page.word_count     = len(text.split())
            page.sentence_count = len(sentences)
            stored, skipped, topics = self._learn_sentences(sentences, url)
            page.facts_extracted = stored + skipped
            page.facts_stored    = stored
            page.facts_skipped   = skipped
            page.top_topics      = topics[:5]
        except Exception as e:
            page.error = str(e)
        page.fetch_time_ms = int((_t.time() - t0) * 1000)
        return page

    # ================================================================
    # HTML → CLEAN TEXT
    # ================================================================

    def _fetch(self, url: str) -> Tuple[str, int]:
        try:
            import requests
            r = requests.get(url, timeout=self.timeout_s,
                             headers={"User-Agent": "Jarvix-Crawler/1.0"},
                             allow_redirects=True)
            return r.text, r.status_code
        except Exception:
            return "", 0

    def _parse_html(self, html: str) -> Tuple[str, str]:
        """
        Clean HTML → (title, plain_text).
        Aggressively removes nav, ads, menus, sidebars, dictionary metadata.
        Keeps only headings and paragraph text from the main content area.
        """
        try:
            from bs4 import BeautifulSoup, Tag
            soup = BeautifulSoup(html, "lxml")
        except Exception:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
            except Exception:
                clean = re.sub(r"<[^>]+>", " ", html)
                return "", re.sub(r"\s+", " ", clean).strip()

        # Title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Step 1: remove structural noise tags
        for tag in soup(list(self.DISCARD_TAGS)):
            tag.decompose()

        # Step 2: remove elements whose class/id looks like nav/ad/menu
        for tag in soup.find_all(True):
            classes = " ".join(tag.get("class", []))
            tag_id  = tag.get("id", "")
            if self.NOISE_PATTERNS.search(classes) or \
               self.NOISE_PATTERNS.search(tag_id):
                tag.decompose()

        # Step 3: prefer semantic main content containers
        body = (
            soup.find("main") or
            soup.find("article") or
            soup.find("div", {"id": re.compile(r"\b(content|main|article|body)\b", re.I)}) or
            soup.find("div", {"class": re.compile(r"\b(content|main|article|post|entry)\b", re.I)}) or
            soup.find("body") or
            soup
        )

        # Step 4: extract only paragraph and heading text
        parts = []
        for tag in body.find_all(["p", "h1", "h2", "h3", "h4", "li"]):
            text = tag.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                parts.append(text)

        text = " ".join(parts)
        return title, text

    # ================================================================
    # SENTENCE FILTERING
    # ================================================================

    def _split_sentences(self, text: str) -> List[str]:
        """Split into sentences and filter out noise."""
        raw = re.split(r"(?<=[.!?])\s+", text)
        out = []
        for s in raw:
            s = s.strip()
            if not s:
                continue
            if self._is_junk(s):
                continue
            out.append(s)
        return out

    def _is_junk(self, sentence: str) -> bool:
        """Return True if the sentence is nav/ad/metadata noise."""
        for pattern in self._JUNK_PATTERNS:
            if pattern.search(sentence):
                return True
        # Reject sentences with too few real words
        words = [w for w in sentence.split()
                 if len(w) > 2 and w.isalpha()]
        if len(words) < 3:
            return True
        # Reject if subject would be a single letter or article fragment
        first_word = sentence.split()[0].lower()
        if len(first_word) <= 2 and first_word not in ("i", "a"):
            return True
        return False

    # ================================================================
    # TRIPLE EXTRACTION
    # ================================================================

    def _extract_triple(self, sentence: str) -> Optional[Tuple[str, str, str]]:
        sent = sentence.strip().rstrip(".")
        for pattern, relation in self._REL_PATTERNS:
            m = pattern.match(sent)
            if not m:
                continue
            subj = self._clean_phrase(m.group(1))
            obj  = self._clean_phrase(m.group(2))
            # Quality gates
            if len(subj) < 2 or len(obj) < 2:
                continue
            if len(subj) > 60 or len(obj) > 120:
                continue
            if obj.count(" ") > 12:
                continue
            # Reject if subject is an article/pronoun fragment
            if subj in ("a", "an", "the", "it", "this", "that",
                        "they", "he", "she", "we", "i", "you"):
                continue
            return subj, relation, obj
        return None

    def _clean_phrase(self, phrase: str) -> str:
        phrase = phrase.strip().lower()
        phrase = re.sub(r"[^a-z0-9 '\-]", "", phrase)
        phrase = re.sub(r"\s+", " ", phrase).strip()
        for art in ("a ", "an ", "the "):
            if phrase.startswith(art):
                phrase = phrase[len(art):]
        return phrase

    # ================================================================
    # STORAGE
    # ================================================================

    def _learn_sentences(self, sentences, source_url) -> Tuple[int, int, list]:
        stored, skipped = 0, 0
        topic_counts    = defaultdict(int)

        for sentence in sentences:
            triple = self._extract_triple(sentence)
            if not triple:
                continue
            subj, rel, obj = triple
            if self.agent.semantic_memory.edge_confidence(subj, rel, obj) > 0.5:
                skipped += 1
                continue
            try:
                self.agent.semantic_memory.add_edge(
                    subj, rel, obj, confidence=0.60, source=source_url)
                self.agent.confidence_mgr.observe(
                    subj, rel, obj, source=source_url, base_confidence=0.60)
                self.agent.brain.graph.add_edge(
                    subj, rel, obj, confidence=0.60, source="web")
                self.agent.memory.add_fact(subj, f"{rel} {obj}", confidence=0.60)
                stored += 1
                topic_counts[subj] += 1
            except Exception:
                skipped += 1

        top = sorted(topic_counts, key=lambda k: -topic_counts[k])
        return stored, skipped, top

    # ================================================================
    # LINKS
    # ================================================================

    def _extract_links(self, base_url, seed_domain) -> List[str]:
        try:
            from bs4 import BeautifulSoup
            html, _ = self._fetch(base_url)
            if not html:
                return []
            soup  = BeautifulSoup(html, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href   = a["href"].strip()
                if not href or href.startswith("#"):
                    continue
                full   = urljoin(base_url, href)
                parsed = urlparse(full)
                if parsed.scheme not in ("http", "https"):
                    continue
                if self.same_domain_only and parsed.netloc != seed_domain:
                    continue
                links.append(full)
            return list(dict.fromkeys(links))
        except Exception:
            return []

    # ================================================================
    # REPORT
    # ================================================================

    def _count_facts(self):
        return sum(len(f) for f in self.agent.memory.facts.values())

    def _top_topics(self, report):
        counts = defaultdict(int)
        for pr in report.page_results:
            for t in pr.top_topics:
                counts[t] += 1
        return sorted(counts, key=lambda k: -counts[k])[:10]

    def _top_facts(self, report):
        seen = set(report.top_topics[:5])
        facts = []
        for (s, r, o), edge in self.agent.semantic_memory.edges.items():
            if "seed" not in edge.sources and s in seen:
                facts.append({"subject": s, "relation": r,
                               "object": o, "confidence": round(edge.confidence, 2)})
        facts.sort(key=lambda x: -x["confidence"])
        return facts[:20]

    def build_evaluation(self, report: CrawlReport) -> dict:
        quality = self._compute_quality(report)
        return {
            "summary": {
                "seed_url":        report.seed_url,
                "pages_visited":   report.pages_visited,
                "pages_failed":    report.pages_failed,
                "total_words":     report.total_words,
                "total_sentences": report.total_sentences,
                "facts_extracted": report.total_facts,
                "facts_stored":    report.stored_facts,
                "duplicates":      report.duplicate_facts,
                "knowledge_gain":  round(report.knowledge_gain, 1),
                "elapsed_ms":      report.elapsed_ms,
                "quality_score":   quality,
            },
            "top_topics":   report.top_topics,
            "top_facts":    report.top_facts,
            "page_results": [
                {"url": pr.url, "title": pr.title or "(no title)",
                 "words": pr.word_count, "sentences": pr.sentence_count,
                 "stored": pr.facts_stored, "skipped": pr.facts_skipped,
                 "top_topics": pr.top_topics, "error": pr.error, "ms": pr.fetch_time_ms}
                for pr in report.page_results
            ],
            "errors":         report.errors,
            "inference_note": self._inference_summary(),
        }

    def _compute_quality(self, report):
        if report.pages_visited == 0:
            return "F — No pages fetched"
        rate = report.stored_facts / max(report.total_sentences, 1)
        if rate > 0.15: return "A — High-density knowledge"
        if rate > 0.08: return "B — Solid factual content"
        if rate > 0.03: return "C — Moderate factual content"
        if report.stored_facts > 0: return "D — Low fact density"
        return "F — No extractable facts"

    def _inference_summary(self):
        try:
            new_facts = self.agent.logic_engine.run()
            if not new_facts:
                return "No new inferences."
            lines = [f"Inferred {len(new_facts)} fact(s):"]
            for r in new_facts[:5]:
                lines.append(f"  {r.subject} {r.relation} {r.object_} "
                             f"({r.confidence:.0%}) via {r.rule_name}")
            return "\n".join(lines)
        except Exception:
            return ""

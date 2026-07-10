"""
Jarvix - Web Crawler Module v3
Advanced HTML filtering, fact extraction, and knowledge integration.
Strips nav/ads/menus/dictionary-metadata.
Only keeps headings + main prose content.
"""

import re
import time
import logging
from urllib.parse import urlparse, urljoin
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Set
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class CrawlQuality(Enum):
    """Quality assessment enum for crawl results."""
    A = "A — High-density knowledge (>15% facts)"
    B = "B — Solid factual content (8-15%)"
    C = "C — Moderate factual content (3-8%)"
    D = "D — Low fact density (0-3%)"
    F = "F — No extractable facts"


@dataclass
class PageResult:
    """Result of processing a single page."""
    url: str
    title: str = ""
    word_count: int = 0
    sentence_count: int = 0
    facts_extracted: int = 0
    facts_stored: int = 0
    facts_skipped: int = 0
    top_topics: list = field(default_factory=list)
    error: str = ""
    fetch_time_ms: int = 0


@dataclass
class CrawlReport:
    """Complete report from a crawl operation."""
    seed_url: str
    pages_visited: int = 0
    pages_failed: int = 0
    total_words: int = 0
    total_sentences: int = 0
    total_facts: int = 0
    stored_facts: int = 0
    duplicate_facts: int = 0
    top_topics: list = field(default_factory=list)
    top_facts: list = field(default_factory=list)
    page_results: list = field(default_factory=list)
    knowledge_gain: float = 0.0
    errors: list = field(default_factory=list)
    elapsed_ms: int = 0


class WebCrawler:
    """
    Production-grade web crawler for fact extraction.
    
    Features:
    - Aggressive HTML noise removal (nav, ads, sidebars)
    - Sentence quality filtering
    - SVO triple extraction
    - Confidence-based deduplication
    - Structured reporting
    """

    # Tags always discarded (navigation, ads, UI chrome)
    DISCARD_TAGS = {
        "script", "style", "nav", "header", "footer", "aside",
        "form", "noscript", "iframe", "svg", "button", "input",
        "select", "textarea", "meta", "link", "figure", "figcaption",
        "picture", "video", "audio", "canvas", "map", "object",
        "table", "sup", "sub", "cite",  # dictionary/wiki noise
    }

    # CSS class/id patterns indicating nav/ad/menu content
    NOISE_PATTERNS = re.compile(
        r"(nav|menu|sidebar|banner|ad|ads|advertisement|cookie|"
        r"popup|modal|footer|header|breadcrumb|pagination|"
        r"related|share|social|comment|login|signup|subscribe|"
        r"toc|contents|infobox|hatnote|catlinks|reflist|"
        r"references|external\.links|see\.also)",
        re.I
    )

    # Sentence quality filters - reject junk patterns
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
                   r"|menu|navigation)\s*$", re.I),        # nav words
        re.compile(r"^(before|after|used|when|"
                   r"consonant sound|vowel sound)\s+", re.I),  # dictionary
        re.compile(r"\b(IPA|pronunciation|phonetic|"
                   r"syllable|hyphenation)\b", re.I),
    ]

    # Relation patterns for SVO triple extraction
    _REL_PATTERNS = [
        (re.compile(r"^(.+?)\s+is\s+an?\s+(.+)$", re.I), "is_a"),
        (re.compile(r"^(.+?)\s+are\s+an?\s+(.+)$", re.I), "is_a"),
        (re.compile(r"^(.+?)\s+is\s+(.+)$", re.I), "has_property"),
        (re.compile(r"^(.+?)\s+are\s+(.+)$", re.I), "has_property"),
        (re.compile(r"^(.+?)\s+has\s+(.+)$", re.I), "has"),
        (re.compile(r"^(.+?)\s+have\s+(.+)$", re.I), "has"),
        (re.compile(r"^(.+?)\s+can\s+(.+)$", re.I), "can"),
        (re.compile(r"^(.+?)\s+causes?\s+(.+)$", re.I), "causes"),
        (re.compile(r"^(.+?)\s+contains?\s+(.+)$", re.I), "has"),
        (re.compile(r"^(.+?)\s+includes?\s+(.+)$", re.I), "has"),
        (re.compile(r"^(.+?)\s+refers?\s+to\s+(.+)$", re.I), "related_to"),
        (re.compile(r"^(.+?)\s+was\s+(.+)$", re.I), "has_property"),
        (re.compile(r"^(.+?)\s+were\s+(.+)$", re.I), "has_property"),
        (re.compile(r"^(.+?)\s+orbits?\s+(.+)$", re.I), "related_to"),
        (re.compile(r"^(.+?)\s+(?:stores?|holds?)\s+(.+)$", re.I), "has"),
        (re.compile(r"^(.+?)\s+(?:produces?|creates?|generates?)\s+(.+)$", re.I), "causes"),
    ]

    # Configuration thresholds
    MIN_PHRASE_LENGTH = 2
    MAX_SUBJECT_LENGTH = 60
    MAX_OBJECT_LENGTH = 120
    MAX_OBJECT_WORDS = 12
    MIN_REAL_WORDS_IN_SENTENCE = 3
    DUPLICATE_CONFIDENCE_THRESHOLD = 0.5
    BASE_TRIPLE_CONFIDENCE = 0.60
    REQUEST_TIMEOUT_SECONDS = 8
    DEFAULT_USER_AGENT = "Jarvix-Crawler/3.0"

    def __init__(
        self,
        agent,
        max_depth: int = 1,
        max_pages: int = 10,
        timeout_s: int = 8,
        same_domain_only: bool = True,
        request_delay_s: float = 0.5,
    ):
        """
        Initialize the web crawler.
        
        Args:
            agent: Jarvix agent instance for memory/knowledge integration
            max_depth: Maximum crawl depth (0 = seed only)
            max_pages: Maximum pages to process
            timeout_s: HTTP request timeout in seconds
            same_domain_only: Whether to restrict crawling to seed domain
            request_delay_s: Delay between requests (politeness)
        """
        self.agent = agent
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout_s = timeout_s
        self.same_domain_only = same_domain_only
        self.request_delay_s = request_delay_s
        self._visited: Set[str] = set()
        self._last_request_time = 0.0

    # ================================================================
    # PUBLIC API
    # ================================================================

    def crawl(self, seed_url: str) -> CrawlReport:
        """
        Crawl a URL, extract facts, and learn from discovered content.
        
        Args:
            seed_url: Starting URL to crawl
            
        Returns:
            CrawlReport with detailed statistics and findings
        """
        t0 = time.time()
        report = CrawlReport(seed_url=seed_url)
        seed_domain = urlparse(seed_url).netloc
        facts_before = self._count_facts()
        queue = [(seed_url, 0)]
        self._visited.clear()

        logger.info(f"Starting crawl from {seed_url}")

        while queue and (report.pages_visited + report.pages_failed) < self.max_pages:
            url, depth = queue.pop(0)
            
            if url in self._visited:
                continue
            
            self._visited.add(url)
            logger.debug(f"Processing {url} (depth={depth})")

            page = self._process_page(url)
            report.page_results.append(page)

            if page.error:
                report.pages_failed += 1
                report.errors.append(f"{url}: {page.error}")
                logger.warning(f"Failed to process {url}: {page.error}")
                continue

            report.pages_visited += 1
            report.total_words += page.word_count
            report.total_sentences += page.sentence_count
            report.total_facts += page.facts_extracted
            report.stored_facts += page.facts_stored
            report.duplicate_facts += page.facts_skipped

            # Queue new links if depth permits
            if depth < self.max_depth:
                new_links = self._extract_links(url, seed_domain)[:5]
                for link in new_links:
                    if link not in self._visited:
                        queue.append((link, depth + 1))
                logger.debug(f"Queued {len(new_links)} new links from {url}")

        report.elapsed_ms = int((time.time() - t0) * 1000)
        facts_after = self._count_facts()
        report.knowledge_gain = (
            (facts_after - facts_before) / max(facts_before, 1) * 100
        )
        report.top_topics = self._top_topics(report)
        report.top_facts = self._top_facts(report)

        logger.info(
            f"Crawl complete: {report.pages_visited} pages, "
            f"{report.stored_facts} facts stored, "
            f"{report.knowledge_gain:.1f}% knowledge gain"
        )

        return report

    # ================================================================
    # PAGE PROCESSING
    # ================================================================

    def _process_page(self, url: str) -> PageResult:
        """Process a single page: fetch, parse, learn."""
        t0 = time.time()
        page = PageResult(url=url)

        try:
            html, status = self._fetch(url)
            if not html:
                page.error = f"HTTP {status} / empty response"
                return page

            title, text = self._parse_html(html)
            page.title = title
            sentences = self._split_sentences(text)
            page.word_count = len(text.split())
            page.sentence_count = len(sentences)

            stored, skipped, topics = self._learn_sentences(sentences, url)
<<<<<<< HEAD
                        page.facts_extracted = stored + skipped
                        page.facts_stored    = stored
                        page.facts_skipped   = skipped
                        page.top_topics      = topics[:5]
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        page.error = str(e)
        page.fetch_time_ms = int((_t.time() - t0) * 1000)
=======
            page.facts_extracted = stored + skipped
            page.facts_stored = stored
            page.facts_skipped = skipped
            page.top_topics = topics[:5]

        except Exception as e:
            page.error = str(e)
            logger.error(f"Error processing {url}: {e}", exc_info=True)

        finally:
            page.fetch_time_ms = int((time.time() - t0) * 1000)

>>>>>>> d446ad2824a2825d981f34a983c1a2023b6a5d7b
        return page

    # ================================================================
    # HTTP & HTML
    # ================================================================

    def _fetch(self, url: str) -> Tuple[str, int]:
        """
        Fetch a URL with timeout and rate limiting.
        
        Returns:
            (html_content, status_code) or ("", 0) on error
        """
        try:
            # Rate limiting (politeness)
            elapsed = time.time() - self._last_request_time
            if elapsed < self.request_delay_s:
                time.sleep(self.request_delay_s - elapsed)
            self._last_request_time = time.time()

            import requests
            r = requests.get(
                url,
                timeout=self.timeout_s,
                headers={"User-Agent": self.DEFAULT_USER_AGENT},
                allow_redirects=True,
            )
            return r.text, r.status_code

        except Exception as e:
            logger.debug(f"Fetch error for {url}: {e}")
            return "", 0

    def _parse_html(self, html: str) -> Tuple[str, str]:
        """
        Parse HTML → (title, clean_text).
        
        Aggressively removes nav, ads, menus, sidebars, dictionary metadata.
        Keeps only headings and paragraph text from main content area.
        """
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            # Fallback to regex if BeautifulSoup fails
            clean = re.sub(r"<[^>]+>", " ", html)
            return "", re.sub(r"\s+", " ", clean).strip()

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Step 1: Remove structural noise tags
        for tag in soup(list(self.DISCARD_TAGS)):
            tag.decompose()

        # Step 2: Remove elements with noisy class/id patterns
        for tag in soup.find_all(True):
            classes = " ".join(tag.get("class", []))
            tag_id = tag.get("id", "")
            if self.NOISE_PATTERNS.search(classes) or self.NOISE_PATTERNS.search(tag_id):
                tag.decompose()

        # Step 3: Prefer semantic main content containers
        body = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", {"id": re.compile(r"\b(content|main|article|body)\b", re.I)})
            or soup.find("div", {"class": re.compile(r"\b(content|main|article|post|entry)\b", re.I)})
            or soup.find("body")
            or soup
        )

        # Step 4: Extract only paragraph and heading text
        parts = []
        for tag in body.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li"]):
            text = tag.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                parts.append(text)

        text = " ".join(parts)
        return title, text

    # ================================================================
    # SENTENCE PROCESSING
    # ================================================================

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences and filter out junk.
        
        Returns:
            List of validated sentences
        """
        raw = re.split(r"(?<=[.!?])\s+", text)
        out = []

        for s in raw:
            s = s.strip()
            if not s or self._is_junk(s):
                continue
            out.append(s)

        return out

    def _is_junk(self, sentence: str) -> bool:
        """
        Classify a sentence as junk (nav/ad/metadata).
        
        Returns:
            True if sentence should be discarded
        """
        # Quick pattern check
        for pattern in self._JUNK_PATTERNS:
            if pattern.search(sentence):
                return True

        # Reject sentences with too few real words
        words = [w for w in sentence.split() if len(w) > 2 and w.isalpha()]
        if len(words) < self.MIN_REAL_WORDS_IN_SENTENCE:
            return True

        # Reject if first word is suspiciously short
        first_word = sentence.split()[0].lower()
        if len(first_word) <= 2 and first_word not in ("i", "a"):
            return True

        return False

    # ================================================================
    # TRIPLE EXTRACTION
    # ================================================================

    def _extract_triple(self, sentence: str) -> Optional[Tuple[str, str, str]]:
        """
        Extract SVO (Subject-Verb-Object) triple from sentence.
        
        Returns:
            (subject, relation, object) or None if no match
        """
        sent = sentence.strip().rstrip(".")

        for pattern, relation in self._REL_PATTERNS:
            m = pattern.match(sent)
            if not m:
                continue

            subj = self._clean_phrase(m.group(1))
            obj = self._clean_phrase(m.group(2))

            # Quality gates
            if (
                len(subj) < self.MIN_PHRASE_LENGTH
                or len(obj) < self.MIN_PHRASE_LENGTH
            ):
                continue
            if len(subj) > self.MAX_SUBJECT_LENGTH or len(obj) > self.MAX_OBJECT_LENGTH:
                continue
            if obj.count(" ") > self.MAX_OBJECT_WORDS:
                continue

            # Reject if subject is article/pronoun
            if subj in ("a", "an", "the", "it", "this", "that", "they", "he", "she", "we", "i", "you"):
                continue

            return subj, relation, obj

        return None

    def _clean_phrase(self, phrase: str) -> str:
        """
        Normalize a phrase: lowercase, remove punctuation, deduplicate articles.
        
        Returns:
            Cleaned phrase
        """
        phrase = phrase.strip().lower()
        phrase = re.sub(r"[^a-z0-9 '\-]", "", phrase)
        phrase = re.sub(r"\s+", " ", phrase).strip()

        # Remove leading articles
        for art in ("a ", "an ", "the "):
            if phrase.startswith(art):
                phrase = phrase[len(art):]

        return phrase

    # ================================================================
    # KNOWLEDGE STORAGE
    # ================================================================

    def _learn_sentences(self, sentences: List[str], source_url: str) -> Tuple[int, int, list]:
        """
        Extract and store triples from sentences.
        
        Returns:
            (stored_count, skipped_count, top_topics)
        """
        stored, skipped = 0, 0
        topic_counts = defaultdict(int)

        for sentence in sentences:
            triple = self._extract_triple(sentence)
            if not triple:
                continue

            subj, rel, obj = triple

            # Check for duplicates using confidence threshold
            try:
                existing_confidence = self.agent.semantic_memory.edge_confidence(subj, rel, obj)
                if existing_confidence > self.DUPLICATE_CONFIDENCE_THRESHOLD:
                    skipped += 1
                    continue
            except Exception:
                pass  # Edge may not exist yet

            # Store the triple in all available memory systems
            try:
                self.agent.semantic_memory.add_edge(
                    subj,
                    rel,
                    obj,
                    confidence=self.BASE_TRIPLE_CONFIDENCE,
                    source=source_url,
                )
                self.agent.confidence_mgr.observe(
                    subj,
                    rel,
                    obj,
                    source=source_url,
                    base_confidence=self.BASE_TRIPLE_CONFIDENCE,
                )
                self.agent.brain.graph.add_edge(
                    subj, rel, obj, confidence=self.BASE_TRIPLE_CONFIDENCE, source="web"
                )
                self.agent.memory.add_fact(subj, f"{rel} {obj}", confidence=self.BASE_TRIPLE_CONFIDENCE)
                stored += 1
                topic_counts[subj] += 1

            except Exception as e:
                logger.debug(f"Failed to store triple ({subj}, {rel}, {obj}): {e}")
                skipped += 1

        top = sorted(topic_counts, key=lambda k: -topic_counts[k])
        return stored, skipped, top

    # ================================================================
    # LINK EXTRACTION
    # ================================================================

    def _extract_links(self, base_url: str, seed_domain: str) -> List[str]:
        """
        Extract unique absolute links from a page.
        
        Returns:
            List of unique URLs (deduplicated, same-domain filtered)
        """
        try:
            from bs4 import BeautifulSoup
            html, _ = self._fetch(base_url)
            if not html:
                return []

            soup = BeautifulSoup(html, "html.parser")
            links = []

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if not href or href.startswith("#"):
                    continue

                full = urljoin(base_url, href)
                parsed = urlparse(full)

                if parsed.scheme not in ("http", "https"):
                    continue

                if self.same_domain_only and parsed.netloc != seed_domain:
                    continue

                links.append(full)

            # Deduplicate while preserving order
            return list(dict.fromkeys(links))

        except Exception as e:
            logger.debug(f"Error extracting links from {base_url}: {e}")
            return []

    # ================================================================
    # REPORTING & METRICS
    # ================================================================

    def _count_facts(self) -> int:
        """Count total facts in agent memory."""
        try:
            return sum(len(f) for f in self.agent.memory.facts.values())
        except Exception:
            return 0

    def _top_topics(self, report: CrawlReport) -> List[str]:
        """Identify top topics across all pages visited."""
        counts = defaultdict(int)
        for pr in report.page_results:
            for t in pr.top_topics:
                counts[t] += 1
        return sorted(counts, key=lambda k: -counts[k])[:10]

    def _top_facts(self, report: CrawlReport) -> List[Dict]:
        """Extract top-confidence facts for top topics."""
        seen = set(report.top_topics[:5])
        facts = []

        try:
            for (s, r, o), edge in self.agent.semantic_memory.edges.items():
                if "seed" not in edge.sources and s in seen:
                    facts.append({
                        "subject": s,
                        "relation": r,
                        "object": o,
                        "confidence": round(edge.confidence, 2),
                    })
        except Exception as e:
            logger.debug(f"Error extracting top facts: {e}")

        facts.sort(key=lambda x: -x["confidence"])
        return facts[:20]

    def build_evaluation(self, report: CrawlReport) -> Dict:
        """
        Build a comprehensive evaluation report.
        
        Returns:
            Dictionary with summary, metrics, and details
        """
        quality = self._compute_quality(report)

        return {
            "summary": {
                "seed_url": report.seed_url,
                "pages_visited": report.pages_visited,
                "pages_failed": report.pages_failed,
                "total_words": report.total_words,
                "total_sentences": report.total_sentences,
                "facts_extracted": report.total_facts,
                "facts_stored": report.stored_facts,
                "duplicates": report.duplicate_facts,
                "knowledge_gain": round(report.knowledge_gain, 1),
                "elapsed_ms": report.elapsed_ms,
                "quality_score": quality,
            },
            "top_topics": report.top_topics,
            "top_facts": report.top_facts,
            "page_results": [
<<<<<<< HEAD
                {"url": pr.url, "title": pr.title or "(no title)",
                 "words": pr.word_count, "sentences": pr.sentence_count,
                 "stored": pr.facts_stored, "skipped": pr.facts_skipped,
                 "top_topics": pr.top_topics, "error": pr.error, "ms": pr.fetch_time_ms}
                 for pr in report.page_results
=======
                {
                    "url": pr.url,
                    "title": pr.title or "(no title)",
                    "words": pr.word_count,
                    "sentences": pr.sentence_count,
                    "stored": pr.facts_stored,
                    "skipped": pr.facts_skipped,
                    "top_topics": pr.top_topics,
                    "error": pr.error,
                    "ms": pr.fetch_time_ms,
                }
                for pr in report.page_results
>>>>>>> d446ad2824a2825d981f34a983c1a2023b6a5d7b
            ],
            "errors": report.errors,
            "inference_note": self._inference_summary(),
        }

    def _compute_quality(self, report: CrawlReport) -> str:
        """Compute quality score based on fact density."""
        if report.pages_visited == 0:
            return CrawlQuality.F.value

        rate = report.stored_facts / max(report.total_sentences, 1)

        if rate > 0.15:
            return CrawlQuality.A.value
        elif rate > 0.08:
            return CrawlQuality.B.value
        elif rate > 0.03:
            return CrawlQuality.C.value
        elif report.stored_facts > 0:
            return CrawlQuality.D.value
        else:
            return CrawlQuality.F.value

    def _inference_summary(self) -> str:
        """Attempt to run inference engine and summarize new facts."""
        try:
            new_facts = self.agent.logic_engine.run()
            if not new_facts:
                return "No new inferences."

            lines = [f"Inferred {len(new_facts)} fact(s):"]
            for r in new_facts[:5]:
                lines.append(
                    f"  {r.subject} {r.relation} {r.object_} "
                    f"({r.confidence:.0%}) via {r.rule_name}"
                )
            return "\n".join(lines)
<<<<<<< HEAD
        except Exception:
            return ""
=======

        except Exception as e:
            logger.debug(f"Inference failed: {e}")
            return ""
>>>>>>> d446ad2824a2825d981f34a983c1a2023b6a5d7b

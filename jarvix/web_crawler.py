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

try:
    import urllib.request as urllib_req
    from bs4 import BeautifulSoup
except ImportError:
    urllib_req = None
    BeautifulSoup = None

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
        re.compile(r"^\s*\[[^\]]+\]\s*$"),  # Matches [edit], [1], [citation needed]
        re.compile(r"^[^a-zA-Z]*$"),  # no letters
        re.compile(r"^\s*\d+\s*$"),  # bare numbers
        re.compile(
            r"(click here|read more|learn more|"
            r"sign up|log in|subscribe|cookie|"
            r"privacy policy|terms of)",
            re.I,
        ),
        re.compile(r"^.{1,10}$"),  # too short
        re.compile(r"^.{400,}$"),  # too long
        re.compile(r"\|.*\|"),  # nav pipe separators
        re.compile(
            r"^\s*(home|about|contact|help|search|menu|navigation)\s*$",
            re.I,
        ),
        re.compile(
            r"^(before|after|used|when|consonant sound|vowel sound)\s+",
            re.I,
        ),
        re.compile(
            r"\b(IPA|pronunciation|phonetic|syllable|hyphenation)\b",
            re.I,
        ),
    ]

    # Patterns for Subject-Verb-Object (SVO) extraction
    _RELATION_PATTERNS = [
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\s]{2,40})\s+(is a|is an|are|was a|was an|were)\s+([a-zA-Z0-9_\s]{2,60})", re.I), "is_a"),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\s]{2,40})\s+(has|have|contains|includes)\s+([a-zA-Z0-9_\s]{2,60})", re.I), "has"),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\s]{2,40})\s+(causes|leads to|results in)\s+([a-zA-Z0-9_\s]{2,60})", re.I), "causes"),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\s]{2,40})\s+(can|is able to)\s+([a-zA-Z0-9_\s]{2,60})", re.I), "can"),
        (re.compile(r"\b([A-Z][a-zA-Z0-9_\s]{2,40})\s+(is located in|is part of)\s+([a-zA-Z0-9_\s]{2,60})", re.I), "part_of"),
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
        """Initialize the web crawler."""
        self.agent = agent
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout_s = timeout_s
        self.same_domain_only = same_domain_only
        self.request_delay_s = request_delay_s
        self._visited: Set[str] = set()
        self._last_request_time = 0.0

    def _rate_limit(self):
        """Politeness delay between outbound HTTP requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay_s:
            time.sleep(self.request_delay_s - elapsed)
        self._last_request_time = time.time()

    def fetch_url(self, url: str) -> Tuple[Optional[str], str]:
        """Fetches URL contents safely with timeouts."""
        if not urllib_req:
            return None, "urllib not available"

        self._rate_limit()
        req = urllib_req.Request(
            url,
            headers={"User-Agent": self.DEFAULT_USER_AGENT}
        )
        try:
            with urllib_req.urlopen(req, timeout=self.timeout_s) as response:
                if not response or not hasattr(response, "headers") or response.headers is None:
                    return None, "Invalid response headers"
                
                content_type = response.headers.get("Content-Type", "") or ""
                if "text/html" not in content_type and "text/plain" not in content_type:
                    return None, f"Unsupported Content-Type: {content_type}"
                
                body = response.read()
                if body is None:
                    return None, "Empty body received"
                
                html_data = body.decode("utf-8", errors="ignore")
                return html_data, ""
        except Exception as e:
            return None, str(e)

    def clean_html(self, html_content: Optional[str]) -> Tuple[str, str, List[str]]:
        """Strips noise tags, headers, nav, ads and returns clean text + inner links."""
        if not BeautifulSoup or not html_content:
            return "", "", []

        soup = BeautifulSoup(html_content, "html.parser")
        if not soup:
            return "", "", []

        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Remove discarded noise tags safely
        for tag in soup.find_all(self.DISCARD_TAGS):
            if tag:
                tag.decompose()

        # Remove elements matching noise patterns
        for element in soup.find_all(True):
            if not element:
                continue
            
            # Safe attribute extractions guarded against None
            elem_id = element.get("id") or ""
            classes = element.get("class") or []
            elem_class = " ".join(classes) if isinstance(classes, list) else str(classes)

            if self.NOISE_PATTERNS.search(elem_id) or self.NOISE_PATTERNS.search(elem_class):
                element.decompose()

        # Extract links safely before dropping link text
        links = []
        for a_tag in soup.find_all("a", href=True):
            if a_tag and a_tag.get("href"):
                href = a_tag.get("href")
                if href:
                    links.append(href)

        text = soup.get_text(separator=" ") or ""
        # Normalize whitespace
        clean_text = re.sub(r"\s+", " ", text).strip()
        return title, clean_text, links

    def is_valid_sentence(self, sentence: Optional[str]) -> bool:
        """Filters out junk lines, navigation links, and unreadable text."""
        if not sentence:
            return False

        sentence_str = sentence.strip()
        if not sentence_str:
            return False

        for pattern in self._JUNK_PATTERNS:
            if pattern.search(sentence_str):
                return False

        words = [w for w in sentence_str.split() if w.isalpha()]
        if len(words) < self.MIN_REAL_WORDS_IN_SENTENCE:
            return False

        return True

    def extract_facts_from_text(self, text: Optional[str]) -> List[Tuple[str, str, str]]:
        """Extracts SVO triples from clean text."""
        if not text:
            return []

        sentences = re.split(r"(?<=[.!?])\s+", text)
        facts = []

        for sent in sentences:
            if not self.is_valid_sentence(sent):
                continue

            for pattern, relation in self._RELATION_PATTERNS:
                match = pattern.search(sent)
                if match:
                    groups = match.groups()
                    if groups and len(groups) >= 3:
                        subj = (groups[0] or "").strip()
                        obj = (groups[2] or "").strip()
                        if (
                            subj and obj
                            and len(subj) <= self.MAX_SUBJECT_LENGTH
                            and len(obj) <= self.MAX_OBJECT_LENGTH
                            and len(obj.split()) <= self.MAX_OBJECT_WORDS
                        ):
                            facts.append((subj, relation, obj))
                            break

        return facts

    def crawl(self, seed_url: str) -> CrawlReport:
        """
        Executes web crawl starting from seed_url.
        Processes pages, cleans HTML, extracts facts, and integrates into memory.
        """
        start_time = time.time()
        report = CrawlReport(seed_url=seed_url)
        queue = [(seed_url, 0)]
        seed_domain = urlparse(seed_url).netloc or ""

        while queue and report.pages_visited < self.max_pages:
            url, depth = queue.pop(0)

            # Normalize URL
            url_clean = url.split("#")[0].rstrip("/")
            if url_clean in self._visited:
                continue

            self._visited.add(url_clean)

            page_start = time.time()
            html, err = self.fetch_url(url_clean)
            fetch_time_ms = int((time.time() - page_start) * 1000)

            if err:
                report.pages_failed += 1
                report.errors.append(f"{url_clean}: {err}")
                report.page_results.append(PageResult(url=url_clean, error=err, fetch_time_ms=fetch_time_ms))
                continue

            title, clean_text, links = self.clean_html(html)
            words = (clean_text or "").split()
            word_count = len(words)
            sentences = [s for s in re.split(r"(?<=[.!?])\s+", clean_text) if self.is_valid_sentence(s)]
            
            facts = self.extract_facts_from_text(clean_text)
            
            stored_count = 0
            skipped_count = 0

            # Integrate into Agent Memory safely
            for s, r, o in facts:
                mem = getattr(self.agent, "semantic_memory", None)
                if mem and hasattr(mem, "add_edge"):
                    edge = mem.add_edge(
                        subject=s,
                        relation=r,
                        object_=o,
                        confidence=self.BASE_TRIPLE_CONFIDENCE,
                        source=url_clean
                    )
                    if edge:
                        stored_count += 1
                    else:
                        skipped_count += 1

            report.pages_visited += 1
            report.total_words += word_count
            report.total_sentences += len(sentences)
            report.total_facts += len(facts)
            report.stored_facts += stored_count
            report.duplicate_facts += skipped_count

            report.page_results.append(PageResult(
                url=url_clean,
                title=title,
                word_count=word_count,
                sentence_count=len(sentences),
                facts_extracted=len(facts),
                facts_stored=stored_count,
                facts_skipped=skipped_count,
                fetch_time_ms=fetch_time_ms
            ))

            # Queue child links if within max depth
            if depth < self.max_depth:
                for link in links:
                    if not link:
                        continue
                    full_link = urljoin(url_clean, link).split("#")[0].rstrip("/")
                    link_domain = urlparse(full_link).netloc or ""

                    if self.same_domain_only and link_domain != seed_domain:
                        continue

                    if full_link not in self._visited:
                        queue.append((full_link, depth + 1))

        report.elapsed_ms = int((time.time() - start_time) * 1000)
        return report
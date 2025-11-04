import re
from typing import Any, Dict, List, Set, Tuple


class DomainDetector:
    def __init__(self) -> None:
        # Raw keyword lists (kept for maintainability); processing below creates
        # faster lookup structures used at runtime.
        self.domain_keywords: Dict[str, List[str]] = {
            "medical": [
                "patient",
                "clinical",
                "medical",
                "diagnosis",
                "treatment",
                "therapy",
                "disease",
                "symptom",
                "healthcare",
                "pharmaceutical",
            ],
            "psychology": [
                "behavior",
                "cognitive",
                "psychological",
                "mental",
                "therapy",
                "intervention",
                "participant",
                "survey",
                "questionnaire",
            ],
            "computer_science": [
                "algorithm",
                "software",
                "programming",
                "data",
                "machine learning",
                "artificial intelligence",
                "network",
                "system",
            ],
            "biology": [
                "species",
                "gene",
                "protein",
                "cell",
                "organism",
                "evolution",
                "molecular",
                "biological",
                "ecosystem",
            ],
            "physics": [
                "quantum",
                "particle",
                "energy",
                "force",
                "wave",
                "electromagnetic",
                "thermodynamic",
                "mechanical",
            ],
            "chemistry": [
                "molecule",
                "compound",
                "reaction",
                "catalyst",
                "chemical",
                "synthesis",
                "analysis",
                "spectroscopy",
            ],
            "social_science": [
                "society",
                "social",
                "community",
                "culture",
                "demographic",
                "survey",
                "interview",
                "ethnographic",
            ],
            "engineering": [
                "design",
                "system",
                "optimization",
                "performance",
                "efficiency",
                "manufacturing",
                "prototype",
                "testing",
            ],
            "economics": [
                "market",
                "economic",
                "financial",
                "price",
                "demand",
                "supply",
                "inflation",
                "gdp",
                "investment",
                "trade",
            ],
            "mathematics": [
                "theorem",
                "proof",
                "equation",
                "function",
                "matrix",
                "calculus",
                "statistics",
                "probability",
                "algebra",
                "geometry",
            ],
            "environmental": [
                "climate",
                "environment",
                "pollution",
                "sustainability",
                "ecosystem",
                "carbon",
                "renewable",
                "conservation",
                "biodiversity",
            ],
            "education": [
                "learning",
                "teaching",
                "curriculum",
                "pedagogy",
                "student",
                "assessment",
                "educational",
                "instruction",
                "classroom",
            ],
            "linguistics": [
                "language",
                "grammar",
                "syntax",
                "phonetics",
                "semantics",
                "discourse",
                "linguistic",
                "morphology",
                "pragmatics",
            ],
            "anthropology": [
                "culture",
                "ethnography",
                "anthropological",
                "ritual",
                "kinship",
                "fieldwork",
                "indigenous",
                "cultural",
                "society",
            ],
            "political_science": [
                "government",
                "policy",
                "political",
                "democracy",
                "election",
                "governance",
                "institution",
                "power",
                "state",
            ],
            "law": [
                "legal",
                "court",
                "judge",
                "statute",
                "constitutional",
                "jurisdiction",
                "precedent",
                "litigation",
                "contract",
            ],
            "business": [
                "management",
                "marketing",
                "strategy",
                "organization",
                "leadership",
                "entrepreneurship",
                "corporate",
                "business",
                "finance",
            ],
            "philosophy": [
                "ethics",
                "metaphysics",
                "epistemology",
                "moral",
                "philosophical",
                "logic",
                "ontology",
                "phenomenology",
                "virtue",
            ],
            "statistics": [
                "statistical",
                "regression",
                "hypothesis",
                "significance",
                "confidence",
                "variance",
                "distribution",
                "sampling",
                "bayesian",
                "inference",
            ],
            "bioinformatics": [
                "genomic",
                "sequencing",
                "bioinformatics",
                "computational biology",
                "phylogenetic",
                "alignment",
                "annotation",
                "database",
                "pipeline",
                "omics",
            ],
            "biomedicine": [
                "biomedical",
                "translational",
                "therapeutic",
                "biomarker",
                "pathogenesis",
                "molecular medicine",
                "precision medicine",
                "drug discovery",
                "clinical trial",
            ],
        }

        # Weights remain explicit for clarity and easy tuning
        self.domain_weights: Dict[str, float] = {
            "medical": 0.35,
            "psychology": 0.25,
            "computer_science": 0.3,
            "biology": 0.3,
            "physics": 0.25,
            "chemistry": 0.25,
            "social_science": 0.25,
            "engineering": 0.3,
            "economics": 0.3,
            "mathematics": 0.35,
            "environmental": 0.3,
            "education": 0.25,
            "linguistics": 0.25,
            "anthropology": 0.25,
            "political_science": 0.25,
            "law": 0.3,
            "business": 0.25,
            "philosophy": 0.2,
            "statistics": 0.4,
            "bioinformatics": 0.35,
            "biomedicine": 0.35,
        }

        # Precompute lookup structures for fast matching
        self._keyword_wordsets: Dict[str, Set[str]] = {}
        self._keyword_phrases: Dict[str, Set[Tuple[str, ...]]] = {}
        self._max_phrase_len: int = 1
        self._build_keyword_lookups()

    def _build_keyword_lookups(self) -> None:
        for domain, keywords in self.domain_keywords.items():
            wordset: Set[str] = set()
            phrases: Set[Tuple[str, ...]] = set()
            for kw in keywords:
                parts = tuple(kw.lower().split())
                if len(parts) == 1:
                    wordset.add(parts[0])
                else:
                    phrases.add(parts)
                    if len(parts) > self._max_phrase_len:
                        self._max_phrase_len = len(parts)
            self._keyword_wordsets[domain] = wordset
            self._keyword_phrases[domain] = phrases

    def detect_domain(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        tokens = self._tokenize_submission(submission)
        if not tokens:
            return {"primary_domain": "general", "confidence": 0.0, "all_scores": {}}

        word_set = set(tokens)
        ngram_sets = self._build_ngram_sets_from_tokens(tokens)

        domain_scores: Dict[str, float] = {
            domain: self._score_domain(domain, word_set, ngram_sets)
            for domain in self.domain_keywords.keys()
        }

        if domain_scores:
            primary_domain = max(domain_scores, key=domain_scores.get)
            denom = max(1, len(self.domain_keywords.get(primary_domain, [])))
            confidence = domain_scores.get(primary_domain, 0.0) / denom
        else:
            primary_domain = "general"
            confidence = 0.0

        return {
            "primary_domain": primary_domain,
            "confidence": min(confidence, 1.0),
            "all_scores": domain_scores,
        }

    def _tokenize_submission(self, submission: Dict[str, Any]) -> List[str]:
        combined = (submission.get("content", "") + " " + submission.get("title", "")).lower()
        return re.findall(r"\w+", combined)

    def _build_ngram_sets_from_tokens(self, tokens: List[str]) -> Dict[int, Set[str]]:
        ngram_sets: Dict[int, Set[str]] = {}
        # range end is exclusive; mirror original behavior: 2 .. max(self._max_phrase_len)
        for n in range(2, max(2, self._max_phrase_len + 1)):
            ngrams = {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}
            ngram_sets[n] = ngrams
        return ngram_sets

    def _score_domain(
        self, domain: str, word_set: Set[str], ngram_sets: Dict[int, Set[str]]
    ) -> float:
        count = 0
        ks = self._keyword_wordsets.get(domain, set())
        if ks:
            count += len(word_set & ks)

        phrases = self._keyword_phrases.get(domain, set())
        if phrases:
            # split phrases into single-word and multi-word groups to simplify logic
            single_word_phrases: Set[str] = set()
            multi_phrase_map: Dict[int, Set[str]] = {}
            for phrase in phrases:
                if len(phrase) == 1:
                    single_word_phrases.add(phrase[0])
                else:
                    phrase_str = " ".join(phrase)
                    multi_phrase_map.setdefault(len(phrase), set()).add(phrase_str)

            if single_word_phrases:
                count += len(word_set & single_word_phrases)

            for n, phrase_set in multi_phrase_map.items():
                ngrams = ngram_sets.get(n, set())
                if ngrams:
                    count += len(phrase_set & ngrams)

        weight = float(self.domain_weights.get(domain, 0.25))
        return count * weight

    def get_domain_specific_weights(self, domain: str) -> Dict[str, float]:
        domain_weights = {
            "medical": {
                "methodology": 0.4,
                "ethics": 0.3,
                "literature": 0.2,
                "clarity": 0.1,
            },
            "psychology": {
                "methodology": 0.35,
                "ethics": 0.25,
                "literature": 0.25,
                "clarity": 0.15,
            },
            "computer_science": {
                "methodology": 0.4,
                "clarity": 0.3,
                "literature": 0.2,
                "ethics": 0.1,
            },
            "biology": {
                "methodology": 0.35,
                "literature": 0.3,
                "ethics": 0.2,
                "clarity": 0.15,
            },
            "physics": {
                "methodology": 0.4,
                "literature": 0.25,
                "clarity": 0.25,
                "ethics": 0.1,
            },
            "chemistry": {
                "methodology": 0.4,
                "literature": 0.25,
                "clarity": 0.25,
                "ethics": 0.1,
            },
            "social_science": {
                "methodology": 0.3,
                "ethics": 0.3,
                "literature": 0.25,
                "clarity": 0.15,
            },
            "engineering": {
                "methodology": 0.4,
                "clarity": 0.3,
                "literature": 0.2,
                "ethics": 0.1,
            },
            "economics": {
                "methodology": 0.35,
                "literature": 0.3,
                "clarity": 0.25,
                "ethics": 0.1,
            },
            "mathematics": {
                "methodology": 0.5,
                "clarity": 0.3,
                "literature": 0.15,
                "ethics": 0.05,
            },
            "environmental": {
                "methodology": 0.35,
                "ethics": 0.25,
                "literature": 0.25,
                "clarity": 0.15,
            },
            "education": {
                "methodology": 0.3,
                "ethics": 0.25,
                "literature": 0.25,
                "clarity": 0.2,
            },
            "linguistics": {
                "methodology": 0.35,
                "literature": 0.3,
                "clarity": 0.25,
                "ethics": 0.1,
            },
            "anthropology": {
                "methodology": 0.3,
                "ethics": 0.3,
                "literature": 0.25,
                "clarity": 0.15,
            },
            "political_science": {
                "methodology": 0.3,
                "literature": 0.3,
                "ethics": 0.2,
                "clarity": 0.2,
            },
            "law": {
                "methodology": 0.25,
                "literature": 0.4,
                "clarity": 0.25,
                "ethics": 0.1,
            },
            "business": {
                "methodology": 0.3,
                "clarity": 0.3,
                "literature": 0.25,
                "ethics": 0.15,
            },
            "philosophy": {
                "literature": 0.4,
                "clarity": 0.3,
                "methodology": 0.2,
                "ethics": 0.1,
            },
            "statistics": {
                "methodology": 0.45,
                "clarity": 0.3,
                "literature": 0.2,
                "ethics": 0.05,
            },
            "bioinformatics": {
                "methodology": 0.4,
                "clarity": 0.25,
                "literature": 0.2,
                "ethics": 0.15,
            },
            "biomedicine": {
                "methodology": 0.35,
                "ethics": 0.3,
                "literature": 0.25,
                "clarity": 0.1,
            },
        }

        return domain_weights.get(
            domain,
            {"methodology": 0.3, "literature": 0.25, "clarity": 0.25, "ethics": 0.2},
        )

    def get_domain_specific_criteria(self, domain: str) -> Dict[str, List[str]]:
        criteria = {
            "medical": {
                "methodology": [
                    "randomization",
                    "blinding",
                    "sample size calculation",
                    "statistical power",
                ],
                "ethics": [
                    "informed consent",
                    "IRB approval",
                    "patient safety",
                    "data privacy",
                ],
                "literature": [
                    "systematic review",
                    "meta-analysis",
                    "clinical guidelines",
                ],
                "clarity": ["medical terminology", "clinical significance"],
            },
            "psychology": {
                "methodology": [
                    "validated instruments",
                    "reliability",
                    "validity",
                    "control groups",
                ],
                "ethics": ["participant consent", "psychological harm", "debriefing"],
                "literature": ["theoretical framework", "psychological constructs"],
                "clarity": ["operational definitions", "statistical reporting"],
            },
            "computer_science": {
                "methodology": [
                    "algorithm complexity",
                    "benchmarking",
                    "reproducibility",
                ],
                "ethics": ["data privacy", "algorithmic bias", "transparency"],
                "literature": ["state-of-the-art comparison", "technical novelty"],
                "clarity": ["code availability", "implementation details"],
            },
            "economics": {
                "methodology": [
                    "econometric models",
                    "causal inference",
                    "robustness checks",
                ],
                "literature": [
                    "economic theory",
                    "empirical evidence",
                    "policy implications",
                ],
                "clarity": ["model specification", "variable definitions"],
                "ethics": ["data sources", "conflicts of interest"],
            },
            "mathematics": {
                "methodology": [
                    "proof rigor",
                    "logical structure",
                    "mathematical notation",
                ],
                "literature": ["theorem citations", "mathematical context"],
                "clarity": ["proof clarity", "notation consistency"],
                "ethics": ["attribution", "originality"],
            },
            "law": {
                "methodology": [
                    "legal analysis",
                    "case law review",
                    "statutory interpretation",
                ],
                "literature": [
                    "precedent analysis",
                    "legal scholarship",
                    "comparative law",
                ],
                "clarity": ["legal reasoning", "argument structure"],
                "ethics": ["bias disclosure", "conflict of interest"],
            },
            "philosophy": {
                "methodology": ["logical argumentation", "conceptual analysis"],
                "literature": [
                    "philosophical tradition",
                    "primary sources",
                    "scholarly debate",
                ],
                "clarity": ["argument structure", "conceptual precision"],
                "ethics": ["intellectual honesty", "fair representation"],
            },
            "statistics": {
                "methodology": [
                    "statistical assumptions",
                    "model validation",
                    "power analysis",
                    "effect size",
                ],
                "literature": ["statistical methods", "comparative studies"],
                "clarity": [
                    "statistical notation",
                    "result interpretation",
                    "visualization",
                ],
                "ethics": ["data integrity", "multiple testing"],
            },
            "bioinformatics": {
                "methodology": [
                    "algorithm validation",
                    "computational pipeline",
                    "database curation",
                    "benchmarking",
                ],
                "literature": ["tool comparison", "method evaluation"],
                "clarity": [
                    "code availability",
                    "workflow documentation",
                    "parameter settings",
                ],
                "ethics": ["data sharing", "privacy protection", "open source"],
            },
            "biomedicine": {
                "methodology": [
                    "experimental design",
                    "biomarker validation",
                    "clinical correlation",
                ],
                "ethics": [
                    "patient consent",
                    "data protection",
                    "clinical ethics",
                    "translational ethics",
                ],
                "literature": [
                    "clinical evidence",
                    "translational research",
                    "therapeutic targets",
                ],
                "clarity": ["clinical relevance", "therapeutic implications"],
            },
        }

        return criteria.get(
            domain,
            {
                "methodology": [
                    "research design",
                    "data collection",
                    "analysis methods",
                ],
                "ethics": ["ethical approval", "participant rights"],
                "literature": ["literature review", "theoretical basis"],
                "clarity": ["writing quality", "presentation"],
            },
        )


domain_detector = DomainDetector()

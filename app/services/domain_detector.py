from typing import Any, Dict, List


class DomainDetector:
    def __init__(self):
        self.domain_keywords = {
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

        self.domain_weights = {
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

    def detect_domain(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        content = (
            submission.get("content", "") + " " + submission.get("title", "")
        ).lower()

        domain_scores = {}
        for domain, keywords in self.domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content)
            domain_scores[domain] = score * self.domain_weights.get(domain, 0.25)

        primary_domain = (
            max(domain_scores, key=domain_scores.get) if domain_scores else "general"
        )
        confidence = domain_scores.get(primary_domain, 0) / len(
            self.domain_keywords.get(primary_domain, [])
        )

        return {
            "primary_domain": primary_domain,
            "confidence": min(confidence, 1.0),
            "all_scores": domain_scores,
        }

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

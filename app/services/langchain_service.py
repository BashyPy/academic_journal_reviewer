import asyncio
import json
import textwrap
from typing import Any, Collection, Dict, List, Optional, cast

from app.utils.logger import get_logger

try:
    from langchain.chains import ConversationChain  # noqa: F401  # pylint: disable=unused-import
except ImportError:
    # Fallback for newer LangChain versions
    class ConversationChain:  # pylint: disable=too-few-public-methods
        def __init__(self, llm, memory, verbose=False):  # pylint: disable=unused-argument
            self.llm = llm
            self.memory = memory

        async def apredict(self, *args, **kwargs):
            # Accept both 'input' and 'prompt' to maintain compatibility
            prompt = kwargs.get("input", kwargs.get("prompt", args[0] if args else None))
            return await self.llm.ainvoke(prompt)

        def predict(self, *args, **kwargs):
            # Accept both 'input' and 'prompt' to maintain compatibility
            prompt = kwargs.get("input", kwargs.get("prompt", args[0] if args else None))
            return self.llm.invoke(prompt)


try:
    from langchain.memory import ConversationBufferWindowMemory as LCConversationBufferWindowMemory
except ImportError:
    # Fallback for newer LangChain versions
    class LCConversationBufferWindowMemory:  # pylint: disable=too-few-public-methods
        def __init__(self, k=10, return_messages=True):
            self.k = k
            self.return_messages = return_messages
            self.messages = []

        def clear(self):
            self.messages = []


try:
    from langchain.schema import Document
except ImportError:
    try:
        from langchain_core.documents import Document  # pylint: disable=ungrouped-imports
    except ImportError:
        # Fallback Document class
        class Document:  # pylint: disable=too-few-public-methods
            def __init__(self, page_content="", metadata=None):
                self.page_content = page_content
                self.metadata = metadata or {}


try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    RecursiveCharacterTextSplitter = None

try:
    from langchain_mongodb import MongoDBAtlasVectorSearch
except ImportError:
    try:
        from langchain_community.vectorstores import MongoDBAtlasVectorSearch
    except ImportError:
        MongoDBAtlasVectorSearch = None

try:
    from langchain_core.messages import HumanMessage
    from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
    from langchain_core.vectorstores import VectorStore
except ImportError:
    HumanMessage = None
    JsonOutputParser = None
    StrOutputParser = None
    VectorStore = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langchain_groq import ChatGroq
except ImportError:
    ChatGroq = None

try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
except ImportError:
    ChatOpenAI = None
    OpenAIEmbeddings = None

from app.core.config import settings  # pylint: disable=ungrouped-imports
from app.services.cache_service import cache_service
from app.services.mongodb_service import mongodb_service

logger = get_logger(__name__)


class LangChainService:
    def __init__(self):
        self.models = self._initialize_models()

        # Initialize embeddings with error handling; fall back to None if unavailable.
        try:
            if settings.OPENAI_API_KEY and OpenAIEmbeddings:
                self.embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
            else:
                self.embeddings = None
                logger.info(
                    "OpenAI API key not set or OpenAIEmbeddings not "
                    "available; embeddings disabled."
                )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(e, {"component": "langchain_service", "function": "__init__"})
            self.embeddings = None

        # Initialize text splitter with fallback to a simple splitter.
        try:
            if RecursiveCharacterTextSplitter:
                self.text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    separators=["\n\n", "\n", ".", " "],
                )
            else:
                raise ImportError("RecursiveCharacterTextSplitter not available")
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception("Failed to initialize RecursiveCharacterTextSplitter"),
                {"component": "langchain_service", "function": "__init__"},
            )

            # Minimal fallback splitter compatible with create_documents
            class SimpleTextSplitter:  # pylint: disable=too-few-public-methods
                def __init__(self, chunk_size=1000, chunk_overlap=200):
                    self.chunk_size = chunk_size
                    self.chunk_overlap = chunk_overlap

                def create_documents(self, texts, metadatas=None):
                    docs = []
                    metadatas = metadatas or [{} for _ in texts]
                    for text, meta in zip(texts, metadatas):
                        text = text or ""
                        step = max(1, self.chunk_size - self.chunk_overlap)
                        for i in range(0, max(1, len(text)), step):
                            chunk = text[i : i + self.chunk_size]
                            docs.append(Document(page_content=chunk, metadata=meta))
                    return docs

            self.text_splitter = SimpleTextSplitter(chunk_size=1000, chunk_overlap=200)

        self.memory = LCConversationBufferWindowMemory(k=10, return_messages=True)
        self.vector_store = self._initialize_vector_store()
        self.domain_prompts = self._load_domain_specific_prompts()

        # Initialize output parsers with fallbacks
        self.output_parsers = {}
        if JsonOutputParser:
            self.output_parsers["json"] = JsonOutputParser()
        if StrOutputParser:
            self.output_parsers["string"] = StrOutputParser()

    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize all LLM models with configurations."""
        models = {}

        # Lightweight local fallback LLM wrapper
        class _DummyLLM:  # pylint: disable=too-few-public-methods
            def __init__(self, name: str):
                self.name = name

            async def ainvoke(self, *args, **kwargs):
                raise RuntimeError(
                    f"LLM provider '{self.name}' is not initialized; "
                    f"set the appropriate API key or choose another provider."
                )

            async def apredict(self, *args, **kwargs):
                raise RuntimeError(
                    f"LLM provider '{self.name}' is not initialized; "
                    f"set the appropriate API key or choose another provider."
                )

        # Provider specifications
        provider_specs = [
            (
                "openai",
                "OPENAI_API_KEY",
                ChatOpenAI,
                {
                    "api_key": settings.OPENAI_API_KEY,
                    "model": "gpt-4-turbo-preview",
                    "temperature": 0.1,
                    "max_tokens": 4000,
                    "request_timeout": 60,
                },
            ),
            (
                "anthropic",
                "ANTHROPIC_API_KEY",
                ChatAnthropic,
                {
                    "api_key": settings.ANTHROPIC_API_KEY,
                    "model": "claude-3-opus-20240229",
                    "temperature": 0.1,
                    "max_tokens": 4000,
                },
            ),
            (
                "gemini",
                "GEMINI_API_KEY",
                ChatGoogleGenerativeAI,
                {
                    "api_key": settings.GEMINI_API_KEY,
                    "model": "gemini-pro",
                    "temperature": 0.1,
                    "max_output_tokens": 4000,
                },
            ),
            (
                "groq",
                "GROQ_API_KEY",
                ChatGroq,
                {
                    "api_key": settings.GROQ_API_KEY,
                    "model": "llama3-8b-8192",
                    "temperature": 0.1,
                    "max_tokens": 4000,
                },
            ),
        ]

        # Loop through provider specs and attempt initialization
        for key, setting_attr, client_cls, kwargs in provider_specs:
            try:
                if getattr(settings, setting_attr, None) and client_cls:
                    # Filter out None values
                    init_kwargs = {k: v for k, v in kwargs.items() if v is not None}
                    models[key] = client_cls(**init_kwargs)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.error(
                    Exception(f"Failed to initialize {key.capitalize()}"),
                    {
                        "component": "langchain_service",
                        "function": "_initialize_models",
                    },
                )

        # Ensure a default provider key exists
        default_provider = getattr(settings, "DEFAULT_LLM", None)
        if default_provider:
            if default_provider not in models:
                logger.warning(
                    "Default LLM provider '%s' is not initialized; using a dummy placeholder.",
                    default_provider,
                )
                models[default_provider] = _DummyLLM(default_provider)
        else:
            # If no default specified and no models initialized
            if not models:
                logger.warning(
                    "No LLM providers initialized and no DEFAULT_LLM set; "
                    "adding a generic dummy provider 'dummy'."
                )
                models["dummy"] = _DummyLLM("dummy")

        # Ensure at least one working model exists
        if not any(not isinstance(model, _DummyLLM) for model in models.values()):
            logger.error(
                Exception(
                    (
                        "No working LLM models initialized; all API keys may be "
                        "invalid or missing."
                    )
                ),
                {
                    "component": "langchain_service",
                    "function": "_initialize_models",
                },
            )

        return models

    def _initialize_vector_store(self) -> Optional[VectorStore]:
        """Initialize vector store for semantic search and retrieval."""
        try:
            if not self.embeddings:
                return None

            # If the MongoDBAtlasVectorSearch class isn't available, skip
            if not MongoDBAtlasVectorSearch:
                logger.info("MongoDBAtlasVectorSearch not available; vector store disabled.")
                return None

            # Cast the motor collection to a typing Collection to satisfy
            # expected parameter types without changing runtime behavior.
            collection = cast(
                Collection[Dict[str, Any]],
                mongodb_service.db["document_embeddings"],
            )

            return MongoDBAtlasVectorSearch(
                collection=collection,
                embedding=self.embeddings,
                index_name="vector_index",
                text_key="content",
                embedding_key="embedding",
            )
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception("Failed to initialize vector store"),
                {
                    "component": "langchain_service",
                    "function": "_initialize_vector_store",
                },
            )
            return None

    def _load_domain_specific_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load domain-specific prompt templates."""
        return {
            "medical": {
                "methodology": (
                    "Analyze medical methodology: randomization, blinding, "
                    "sample size, statistical power, IRB approval"
                ),
                "literature": (
                    "Evaluate medical literature: systematic reviews, "
                    "clinical guidelines, evidence hierarchy"
                ),
                "ethics": (
                    "Assess medical ethics: informed consent, patient safety, " "data privacy"
                ),
                "clarity": (
                    "Review medical clarity: terminology, clinical "
                    "significance, statistical reporting"
                ),
            },
            "psychology": {
                "methodology": (
                    "Analyze psychological methodology: validated instruments, "
                    "reliability, validity, controls"
                ),
                "literature": (
                    "Evaluate psychology literature: theoretical frameworks, "
                    "constructs, evidence"
                ),
                "ethics": (
                    "Assess psychological ethics: participant consent, harm "
                    "prevention, debriefing"
                ),
                "clarity": (
                    "Review psychology clarity: operational definitions, " "statistical reporting"
                ),
            },
            "computer_science": {
                "methodology": (
                    "Analyze CS methodology: algorithm complexity, " "benchmarking, reproducibility"
                ),
                "literature": (
                    "Evaluate CS literature: state-of-art comparisons, " "technical novelty"
                ),
                "ethics": ("Assess CS ethics: data privacy, algorithmic bias, " "transparency"),
                "clarity": ("Review CS clarity: code documentation, implementation " "details"),
            },
            "biology": {
                "methodology": (
                    "Analyze biological methodology: experimental design, "
                    "controls, statistical analysis"
                ),
                "literature": (
                    "Evaluate biology literature: evolutionary context, " "molecular mechanisms"
                ),
                "ethics": ("Assess biological ethics: animal welfare, environmental " "impact"),
                "clarity": (
                    "Review biology clarity: species identification, " "methodology description"
                ),
            },
            "physics": {
                "methodology": (
                    "Analyze physics methodology: experimental setup, "
                    "measurement precision, error analysis"
                ),
                "literature": (
                    "Evaluate physics literature: theoretical foundations, "
                    "experimental validation"
                ),
                "ethics": (
                    "Assess physics ethics: safety protocols, environmental " "considerations"
                ),
                "clarity": ("Review physics clarity: mathematical notation, unit " "consistency"),
            },
            "mathematics": {
                "methodology": (
                    "Analyze mathematical methodology: proof rigor, logical " "structure"
                ),
                "literature": (
                    "Evaluate mathematics literature: theorem citations, " "mathematical context"
                ),
                "ethics": "Assess mathematical ethics: attribution, originality",
                "clarity": ("Review mathematics clarity: proof structure, notation " "consistency"),
            },
            "economics": {
                "methodology": (
                    "Analyze economic methodology: econometric models, causal " "inference"
                ),
                "literature": (
                    "Evaluate economics literature: economic theory, empirical " "evidence"
                ),
                "ethics": ("Assess economic ethics: data sources, conflicts of " "interest"),
                "clarity": (
                    "Review economics clarity: model specification, variable " "definitions"
                ),
            },
            "law": {
                "methodology": (
                    "Analyze legal methodology: case law analysis, statutory " "interpretation"
                ),
                "literature": (
                    "Evaluate legal literature: precedent analysis, legal " "scholarship"
                ),
                "ethics": ("Assess legal ethics: bias disclosure, conflict of " "interest"),
                "clarity": ("Review legal clarity: argument structure, legal reasoning"),
            },
            "statistics": {
                "methodology": (
                    "Analyze statistical methodology: assumptions, model "
                    "validation, power analysis"
                ),
                "literature": (
                    "Evaluate statistics literature: method comparisons, "
                    "theoretical developments"
                ),
                "ethics": ("Assess statistical ethics: data integrity, multiple " "testing"),
                "clarity": (
                    "Review statistics clarity: notation, interpretation, " "visualization"
                ),
            },
            "bioinformatics": {
                "methodology": (
                    "Analyze bioinformatics methodology: algorithm validation, " "pipeline design"
                ),
                "literature": (
                    "Evaluate bioinformatics literature: tool comparisons, " "benchmarking"
                ),
                "ethics": ("Assess bioinformatics ethics: data sharing, privacy " "protection"),
                "clarity": (
                    "Review bioinformatics clarity: code availability, " "workflow documentation"
                ),
            },
        }

    async def create_document_embeddings(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """Create and store document embeddings for semantic search."""
        if not self.embeddings or not self.vector_store:
            logger.info("Embeddings or vector store not available, skipping embedding creation")
            return []

        try:
            # Truncate content if too long to avoid memory issues
            max_content_length = 50000  # Reasonable limit for embeddings
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
                logger.info(
                    "Content truncated to %d characters for embedding",
                    max_content_length,
                )

            # Split document into chunks
            documents = self.text_splitter.create_documents([content], [metadata])

            # Limit number of chunks to avoid overwhelming the system
            if len(documents) > 20:
                documents = documents[:20]
                logger.info("Limited to first 20 document chunks for embedding")

            # Store embeddings with timeout
            result = await asyncio.wait_for(
                self.vector_store.aadd_documents(documents), timeout=30.0
            )
            # Handle different return types from vector store
            if isinstance(result, list):
                return result
            # Return document count as fallback
            return [str(i) for i in range(len(documents))]
        except asyncio.TimeoutError:
            logger.error(
                Exception("Embedding creation timed out"),
                {
                    "component": "langchain_service",
                    "function": "create_document_embeddings",
                },
            )
            return []
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception(f"Failed to create document embeddings: {str(e)}"),
                {
                    "component": "langchain_service",
                    "function": "create_document_embeddings",
                },
            )
            return []

    def _validate_and_get_model(self, provider: Optional[str]):
        """Validate provider and return (provider, model)."""
        provider = provider or settings.DEFAULT_LLM
        if not provider:
            raise ValueError("No provider specified and DEFAULT_LLM is not set.")
        model = self.models.get(provider)
        if model is None:
            raise ValueError(f"Requested provider '{provider}' is not initialized.")
        return provider, model

    async def _get_cached_response(self, cache_key: str, provider: str) -> Optional[str]:
        """Try to get a cached response."""
        try:
            return await cache_service.get(cache_key, provider)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception("_get_cached_response failed"),
                {
                    "component": "langchain_service",
                    "function": "_get_cached_response",
                },
            )
            return None

    async def _get_rag_context(self, prompt: str) -> str:
        """Retrieve relevant RAG context via semantic search."""
        try:
            relevant_docs = await self.semantic_search(prompt)
            return "\n\n".join(
                [getattr(doc, "page_content", str(doc)) for doc in relevant_docs[:3]]
            )
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception("_get_rag_context failed"),
                {
                    "component": "langchain_service",
                    "function": "_get_rag_context",
                },
            )
            return ""

    async def semantic_search(self, query: str, k: int = 5) -> List[Document]:
        """Perform semantic search against the vector store."""
        try:
            if not self.vector_store or not self.embeddings:
                logger.info("Vector store or embeddings not available, skipping semantic search")
                return []

            # Truncate query if too long
            if len(query) > 1000:
                query = query[:1000]
                logger.info("Query truncated for semantic search")

            # Add timeout to prevent hanging
            search_result = await asyncio.wait_for(self._perform_search(query, k), timeout=10.0)
            return search_result
        except asyncio.TimeoutError:
            logger.error(
                Exception("Semantic search timed out"),
                {
                    "component": "langchain_service",
                    "function": "semantic_search",
                },
            )
            return []
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception(f"semantic_search failed: {str(e)}"),
                {"component": "langchain_service", "function": "semantic_search"},
            )
            return []

    async def _perform_search(self, query: str, k: int) -> List[Document]:
        """Helper method to perform the actual search with fallbacks."""
        try:
            # Try async methods first
            if hasattr(self.vector_store, "asimilarity_search"):
                result = await self.vector_store.asimilarity_search(query, k=k)
                # Result should already be a list from asimilarity_search
                return result if isinstance(result, list) else []

            # Fallback to sync method in thread pool
            if hasattr(self.vector_store, "similarity_search"):
                import concurrent.futures  # pylint: disable=import-outside-toplevel

                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result = await loop.run_in_executor(
                        executor,
                        lambda: self.vector_store.similarity_search(query, k=k),
                    )
                    return list(result) if result else []

            return []
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception(f"_perform_search failed: {str(e)}"),
                {
                    "component": "langchain_service",
                    "function": "_perform_search",
                },
            )
            return []

    async def _invoke_model(
        self, model: Any, provider: str, enhanced_prompt: str, _use_memory: bool
    ) -> str:
        """Invoke the model and normalize the response to a string."""
        try:
            # Use basic LLM service as fallback
            from app.services.llm_service import (  # pylint: disable=import-outside-toplevel
                llm_service,
            )

            # Try LangChain model first, fallback to basic LLM service
            try:
                response = None
                if hasattr(model, "ainvoke"):
                    if HumanMessage:
                        response = await model.ainvoke([HumanMessage(content=enhanced_prompt)])
                    else:
                        response = await model.ainvoke(enhanced_prompt)
                elif hasattr(model, "apredict"):
                    response = await model.apredict(enhanced_prompt)
                else:
                    # Fallback to basic LLM service
                    return await llm_service.generate_content(enhanced_prompt, provider)

                # Normalize response to string
                if hasattr(response, "content"):
                    return response.content
                if isinstance(response, dict):
                    return json.dumps(response)
                return str(response)

            except Exception:  # pylint: disable=broad-exception-caught
                # Fallback to basic LLM service
                return await llm_service.generate_content(enhanced_prompt, provider)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception(f"_invoke_model failed: {str(e)}"),
                {"component": "langchain_service", "function": "_invoke_model"},
            )
            return f"Error: Model invocation failed - {str(e)}"

    async def invoke_with_rag(
        self,
        prompt: str,
        provider: str = None,
        context: Dict[str, Any] = None,
        use_memory: bool = True,
    ) -> str:
        """Invoke LLM with Retrieval-Augmented Generation."""
        try:
            # Validate provider and get model
            try:
                provider, model = self._validate_and_get_model(provider)
            except ValueError as ve:
                msg = str(ve)
                logger.warning("invoke_with_rag error: %s", msg)
                return f"Error: {msg}"

            # Generate cache key and check cache
            cache_key = self._generate_cache_key(prompt, provider, context)
            cached_response = await self._get_cached_response(cache_key, provider)
            if cached_response:
                return cached_response

            # Retrieve RAG context (best-effort)
            rag_context = await self._get_rag_context(prompt)

            # Build enhanced prompt
            enhanced_prompt = self._build_rag_prompt(prompt, context, rag_context)

            # Invoke the model
            try:
                response = await self._invoke_model(model, provider, enhanced_prompt, use_memory)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.error(
                    Exception(f"Model invocation failed for provider '{provider}'"),
                    {
                        "component": "langchain_service",
                        "function": "invoke_with_rag",
                    },
                )
                return f"Error: Model invocation failed for provider '{provider}'"

            # Best-effort cache store
            try:
                await self._cache_response(cache_key, provider, response)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.error(
                    Exception("Failed to cache response (non-fatal)"),
                    {
                        "component": "langchain_service",
                        "function": "invoke_with_rag",
                    },
                )

            return response

        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception("invoke_with_rag unexpected failure"),
                {
                    "component": "langchain_service",
                    "function": "invoke_with_rag",
                },
            )
            return "Error: Unexpected failure"

    async def multi_model_consensus(
        self, prompt: str, context: Dict[str, Any] = None, models: List[str] = None
    ) -> str:
        """Get consensus from multiple models for critical decisions."""
        models = models or ["groq"]

        # Enhance prompt with requirements for detailed analysis
        enhanced_prompt = f"""
{prompt}

IMPORTANT ANALYSIS REQUIREMENTS:
- Provide comprehensive, detailed findings
- Quote exact text from manuscript for each issue
- Reference specific sections and line numbers
- Classify severity (major/moderate/minor) for each finding
- Give concrete, actionable recommendations
- Include confidence level (0-1) in assessment
- Confirm objective, unbiased analysis
- Maintain professional academic tone

Ensure thorough coverage of all critical aspects with specific evidence.
"""

        # Try each model until one succeeds
        for model in models:
            try:
                response = await self.invoke_with_rag(
                    enhanced_prompt, model, context, use_memory=False
                )
                if not response.startswith("Error:"):
                    return response
            except Exception:  # pylint: disable=broad-exception-caught
                logger.error(
                    Exception(f"multi_model_consensus error for model '{model}'"),
                    {
                        "component": "langchain_service",
                        "function": "multi_model_consensus",
                    },
                )
                continue

        # If all models fail, return a basic response
        return "Multi-model consensus failed. " "Using single model fallback for ethics review."

    async def domain_aware_review(
        self,
        content: str,
        domain: str,
        review_type: str,
        context: Dict[str, Any] = None,
    ) -> str:
        """Perform domain-aware review using specialized prompts."""
        try:
            # Defensively handle None context
            context = context or {}

            # Get domain-specific prompt template
            domain_prompts = self.domain_prompts.get(domain, {})
            base_prompt = (
                domain_prompts.get(review_type)
                or f"Perform a {review_type} review of this {domain} manuscript."
            )

            # Truncate content appropriately for the review type
            max_content_length = 6000 if review_type in ["methodology", "literature"] else 4000
            truncated_content = content[:max_content_length]
            if len(content) > max_content_length:
                truncated_content += "\n\n[Content truncated for analysis]"

            # Create comprehensive prompt using dedent to normalize indentation
            full_prompt = textwrap.dedent(
                f"""
            {base_prompt}

            Document Title: {context.get('title', 'Unknown')}
            Domain: {domain}
            Pages: {context.get('metadata', {}).get('pages', 'Unknown')}

            Content:
            {truncated_content}

            Provide DETAILED structured analysis with:
            1. Score (0-10) with clear justification
            2. Strengths (3-5 specific points with evidence)
            3. Weaknesses (3-5 specific points with quoted text)
            4. Detailed findings with:
               - Exact quoted text from manuscript
               - Section and line references
               - Severity classification (major/moderate/minor)
               - Specific improvement recommendations
            5. Critical issues requiring immediate attention
            6. Confidence level (0-1) in assessment
            7. Bias check confirmation

            IMPORTANT:
            - Quote exact text for each finding
            - Reference specific sections and line numbers
            - Provide actionable, concrete recommendations
            - Consider domain-specific standards and conventions
            - Ensure professional academic tone

            Format response with clear sections and detailed evidence.
            """
            ).strip()

            # Invoke with RAG and return response
            response = await self.invoke_with_rag(full_prompt, context=context, use_memory=False)
            return response

        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception("domain_aware_review failed"),
                {
                    "component": "langchain_service",
                    "function": "domain_aware_review",
                },
            )
            return "Error: domain_aware_review failed"

    async def chain_of_thought_analysis(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Perform step-by-step chain-of-thought analysis."""
        context = context or {}

        # Truncate prompt for chain-of-thought to avoid token limits
        if len(prompt) > 8000:
            prompt = prompt[:8000] + "\n\n[Content truncated for analysis]"

        cot_prompt = f"""
        Analyze this step-by-step using chain-of-thought reasoning:

        {prompt}

        Please think through this systematically:
        1. First, identify the key components to analyze
        2. Then, examine each component in detail with specific evidence:
           - Quote exact text from the manuscript
           - Reference section and line numbers
           - Identify specific issues or strengths
        3. Consider the relationships between components
        4. Evaluate strengths and weaknesses with concrete examples
        5. Synthesize findings into actionable insights with:
           - Severity classification (major/moderate/minor)
           - Specific recommendations for improvement
           - Confidence level in assessment

        CRITICAL REQUIREMENTS:
        - Provide detailed evidence for each finding
        - Quote exact text where issues occur
        - Give specific, actionable recommendations
        - Maintain professional academic tone
        - Show clear reasoning at each step
        """

        return await self.invoke_with_rag(cot_prompt, context=context)

    def _build_rag_prompt(self, prompt: str, context: Dict[str, Any], rag_context: str) -> str:
        """Build enhanced prompt with RAG context."""
        context_info = []

        if context:
            if "domain" in context:
                context_info.append(f"Academic Domain: {context['domain']}")
            if "metadata" in context:
                meta = context["metadata"]
                if "pages" in meta:
                    context_info.append(f"Document Length: {meta['pages']} pages")
                if "file_type" in meta:
                    context_info.append(f"Format: {meta['file_type'].upper()}")

        context_str = "\n".join(context_info) if context_info else "No additional context provided."

        # Truncate RAG context if too long
        if len(rag_context) > 2000:
            rag_context = rag_context[:2000] + "..."

        # Truncate main prompt if too long
        if len(prompt) > 8000:
            prompt = prompt[:8000] + "..."

        prompt_template = f"""
        Context Information:
        {context_str}

        Relevant Background Knowledge:
        {rag_context}

        Task:
        {prompt}

        Please provide a comprehensive response considering both the context and background knowledge.
        """

        # Remove leading indentation and ensure total length is reasonable
        final_prompt = textwrap.dedent(prompt_template).strip()

        # Final safety check for token limits
        max_chars = 40000
        if len(final_prompt) > max_chars:
            final_prompt = final_prompt[:max_chars] + "\n\n[Content truncated due to length limits]"

        return final_prompt

    def _generate_cache_key(self, prompt: str, provider: str, context: Dict[str, Any]) -> str:
        """Generate cache key for complex requests."""
        import hashlib  # pylint: disable=import-outside-toplevel

        key_data = {
            "prompt": prompt[:500],
            "provider": provider,
            "context": context,
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

    async def _cache_response(self, cache_key: str, provider: str, response: str) -> None:
        """Cache the response using the cache service."""
        try:
            await cache_service.set(cache_key, provider, response)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.error(
                Exception("Failed to cache response"),
                {
                    "component": "langchain_service",
                    "function": "_cache_response",
                },
            )

    def cleanup_memory(self):
        """Clean up conversation memory."""
        self.memory.clear()


langchain_service = LangChainService()

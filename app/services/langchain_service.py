import json
import textwrap
import logging
from typing import Any, Dict, List, Optional

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import Document
from langchain_anthropic import ChatAnthropic
from langchain_community.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.vectorstores import VectorStore
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings
from app.services.cache_service import cache_service
from app.services.mongodb_service import mongodb_service

logger = logging.getLogger(__name__)


class LangChainService:
    def __init__(self):
        self.models = self._initialize_models()

        # Initialize embeddings with error handling; fall back to None if unavailable.
        try:
            if settings.OPENAI_API_KEY:
                self.embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
            else:
                self.embeddings = None
                logger.info("OpenAI API key not set; embeddings disabled.")
        except Exception as e:
            logger.exception(
                e,
                "Failed to initialize OpenAI embeddings"
            )
            self.embeddings = None

        # Initialize text splitter with fallback to a simple splitter to ensure create_documents exists.
        try:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ".", " "],
            )
        except Exception:
            logger.exception("Failed to initialize RecursiveCharacterTextSplitter")

            # Minimal fallback splitter compatible with create_documents used elsewhere.
            class SimpleTextSplitter:
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

        self.memory = ConversationBufferWindowMemory(k=10, return_messages=True)
        self.vector_store = self._initialize_vector_store()
        self.domain_prompts = self._load_domain_specific_prompts()
        self.output_parsers = {"json": JsonOutputParser(), "string": StrOutputParser()}

    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize all LLM models with configurations and provide clear fallbacks."""
        models = {}

        # Lightweight local fallback LLM wrapper that raises informative errors on use.
        class _DummyLLM:
            def __init__(self, name: str):
                self.name = name

            async def ainvoke(self, *args, **kwargs):
                raise RuntimeError(
                    f"LLM provider '{self.name}' is not initialized; set the appropriate API key or choose another provider."
                )

            async def apredict(self, *args, **kwargs):
                raise RuntimeError(
                    f"LLM provider '{self.name}' is not initialized; set the appropriate API key or choose another provider."
                )

        try:
            if settings.OPENAI_API_KEY:
                models["openai"] = ChatOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    model="gpt-4-turbo-preview",
                    temperature=0.1,
                    max_tokens=4000,
                    request_timeout=60,
                )
        except Exception:
            logger.exception("Failed to initialize OpenAI")

        try:
            if settings.ANTHROPIC_API_KEY:
                models["anthropic"] = ChatAnthropic(
                    api_key=settings.ANTHROPIC_API_KEY,
                    model="claude-3-opus-20240229",
                    temperature=0.1,
                    max_tokens=4000,
                )
        except Exception:
            logger.exception("Failed to initialize Anthropic")

        try:
            if settings.GEMINI_API_KEY:
                models["gemini"] = ChatGoogleGenerativeAI(
                    api_key=settings.GEMINI_API_KEY,
                    model="gemini-pro",
                    temperature=0.1,
                    max_output_tokens=4000,
                )
        except Exception:
            logger.exception("Failed to initialize Gemini")

        try:
            if settings.GROQ_API_KEY:
                models["groq"] = ChatGroq(
                    api_key=settings.GROQ_API_KEY,
                    model="llama3-70b-8192",
                    temperature=0.1,
                    max_tokens=4000,
                )
        except Exception:
            logger.exception("Failed to initialize Groq")

        # Ensure a default provider key exists to avoid KeyError later; use dummy wrapper if real model missing.
        default_provider = getattr(settings, "DEFAULT_LLM", None)
        if default_provider:
            if default_provider not in models:
                logger.warning(
                    "Default LLM provider '%s' is not initialized; using a dummy placeholder that will raise an informative error on use.",
                    default_provider,
                )
                models[default_provider] = _DummyLLM(default_provider)
        else:
            # If no default specified and no models initialized, add a generic dummy to guide the user.
            if not models:
                logger.warning(
                    "No LLM providers initialized and no DEFAULT_LLM set; adding a generic dummy provider 'dummy' to avoid KeyError."
                )
                models["dummy"] = _DummyLLM("dummy")

        return models

    def _initialize_vector_store(self) -> Optional[VectorStore]:
        """Initialize vector store for semantic search and retrieval."""
        try:
            if not self.embeddings:
                return None
            return MongoDBAtlasVectorSearch(
                collection=mongodb_service.db["document_embeddings"],
                embedding=self.embeddings,
                index_name="vector_index",
                text_key="content",
                embedding_key="embedding",
            )
        except Exception:
            logger.exception("Failed to initialize vector store")
            return None

    def _load_domain_specific_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load domain-specific prompt templates."""
        return {
            "medical": {
                "methodology": "Analyze medical methodology: randomization, blinding, sample size, statistical power, IRB approval",
                "literature": "Evaluate medical literature: systematic reviews, clinical guidelines, evidence hierarchy",
                "ethics": "Assess medical ethics: informed consent, patient safety, data privacy",
                "clarity": "Review medical clarity: terminology, clinical significance, statistical reporting",
            },
            "psychology": {
                "methodology": "Analyze psychological methodology: validated instruments, reliability, validity, controls",
                "literature": "Evaluate psychology literature: theoretical frameworks, constructs, evidence",
                "ethics": "Assess psychological ethics: participant consent, harm prevention, debriefing",
                "clarity": "Review psychology clarity: operational definitions, statistical reporting",
            },
            "computer_science": {
                "methodology": "Analyze CS methodology: algorithm complexity, benchmarking, reproducibility",
                "literature": "Evaluate CS literature: state-of-art comparisons, technical novelty",
                "ethics": "Assess CS ethics: data privacy, algorithmic bias, transparency",
                "clarity": "Review CS clarity: code documentation, implementation details",
            },
            "biology": {
                "methodology": "Analyze biological methodology: experimental design, controls, statistical analysis",
                "literature": "Evaluate biology literature: evolutionary context, molecular mechanisms",
                "ethics": "Assess biological ethics: animal welfare, environmental impact",
                "clarity": "Review biology clarity: species identification, methodology description",
            },
            "physics": {
                "methodology": "Analyze physics methodology: experimental setup, measurement precision, error analysis",
                "literature": "Evaluate physics literature: theoretical foundations, experimental validation",
                "ethics": "Assess physics ethics: safety protocols, environmental considerations",
                "clarity": "Review physics clarity: mathematical notation, unit consistency",
            },
            "mathematics": {
                "methodology": "Analyze mathematical methodology: proof rigor, logical structure",
                "literature": "Evaluate mathematics literature: theorem citations, mathematical context",
                "ethics": "Assess mathematical ethics: attribution, originality",
                "clarity": "Review mathematics clarity: proof structure, notation consistency",
            },
            "economics": {
                "methodology": "Analyze economic methodology: econometric models, causal inference",
                "literature": "Evaluate economics literature: economic theory, empirical evidence",
                "ethics": "Assess economic ethics: data sources, conflicts of interest",
                "clarity": "Review economics clarity: model specification, variable definitions",
            },
            "law": {
                "methodology": "Analyze legal methodology: case law analysis, statutory interpretation",
                "literature": "Evaluate legal literature: precedent analysis, legal scholarship",
                "ethics": "Assess legal ethics: bias disclosure, conflict of interest",
                "clarity": "Review legal clarity: argument structure, legal reasoning",
            },
            "statistics": {
                "methodology": "Analyze statistical methodology: assumptions, model validation, power analysis",
                "literature": "Evaluate statistics literature: method comparisons, theoretical developments",
                "ethics": "Assess statistical ethics: data integrity, multiple testing",
                "clarity": "Review statistics clarity: notation, interpretation, visualization",
            },
            "bioinformatics": {
                "methodology": "Analyze bioinformatics methodology: algorithm validation, pipeline design",
                "literature": "Evaluate bioinformatics literature: tool comparisons, benchmarking",
                "ethics": "Assess bioinformatics ethics: data sharing, privacy protection",
                "clarity": "Review bioinformatics clarity: code availability, workflow documentation",
            },
        }

    async def create_document_embeddings(
        self, content: str, metadata: Dict[str, Any]
    ) -> List[str]:
        """Create and store document embeddings for semantic search."""
        if not self.vector_store:
            return []

        # Split document into chunks
        documents = self.text_splitter.create_documents([content], [metadata])

        # Store embeddings with error handling
        try:
            doc_ids = await self.vector_store.aadd_documents(documents)
            return doc_ids
        except Exception:
            # Log the error and return empty list to indicate failure
            logger.exception("Failed to create document embeddings")
            return []

    def _validate_and_get_model(self, provider: Optional[str]):
        """Validate provider and return (provider, model) or raise ValueError with message."""
        provider = provider or settings.DEFAULT_LLM
        if not provider:
            raise ValueError("No provider specified and DEFAULT_LLM is not set.")
        model = self.models.get(provider)
        if model is None:
            raise ValueError(f"Requested provider '{provider}' is not initialized.")
        return provider, model

    async def _get_cached_response(
        self, cache_key: str, provider: str
    ) -> Optional[str]:
        """Try to get a cached response; on failure return None and log."""
        try:
            return await cache_service.get(cache_key, provider)
        except Exception:
            logger.exception("_get_cached_response failed")
            return None

    async def _get_rag_context(self, prompt: str) -> str:
        """Retrieve relevant RAG context via semantic search, returning empty string on failure."""
        try:
            relevant_docs = await self.semantic_search(prompt)
            # defensively access page_content in case returned items are dicts or other types
            return "\n\n".join(
                [getattr(doc, "page_content", str(doc)) for doc in relevant_docs[:3]]
            )
        except Exception:
            logger.exception("_get_rag_context failed")
            return ""

    async def semantic_search(self, query: str, k: int = 5) -> List[Document]:
        """Perform semantic search against the vector store with robust error handling and fallbacks."""
        try:
            if not self.vector_store:
                return []
            # Prefer async search methods if available, otherwise fall back to sync variants.
            if hasattr(self.vector_store, "asimilarity_search"):
                return await self.vector_store.asimilarity_search(query, k=k)
            if hasattr(self.vector_store, "asimilarity_search_by_vector"):
                return await self.vector_store.asimilarity_search_by_vector(query, k=k)
            if hasattr(self.vector_store, "similarity_search"):
                # some vectorstores only expose sync similarity_search
                return self.vector_store.similarity_search(query, k=k)
            # If no known method is present, return empty result rather than raising.
            return []
        except Exception:
            logger.exception("semantic_search failed")
            return []

    async def _invoke_model(
        self, model: Any, provider: str, enhanced_prompt: str, use_memory: bool
    ) -> str:
        """Invoke the model or ConversationChain and normalize the response to a string."""
        try:
            # Handle memory-enabled conversation chain
            if use_memory:
                chain = ConversationChain(llm=model, memory=self.memory, verbose=False)
                if hasattr(chain, "apredict"):
                    response = await chain.apredict(input=enhanced_prompt)
                elif hasattr(chain, "predict"):
                    response = chain.predict(input=enhanced_prompt)
                else:
                    raise RuntimeError(
                        "ConversationChain has no supported predict methods."
                    )
            else:
                if hasattr(model, "apredict"):
                    response = await model.apredict(enhanced_prompt)
                elif hasattr(model, "ainvoke"):
                    maybe_msg = await model.ainvoke(
                        [HumanMessage(content=enhanced_prompt)]
                    )
                    response = getattr(maybe_msg, "content", maybe_msg)
                elif hasattr(model, "predict"):
                    response = model.predict(enhanced_prompt)
                else:
                    raise RuntimeError(
                        f"Model '{provider}' has no supported async/sync invocation methods."
                    )

            # Normalize response to a string
            if isinstance(response, dict):
                return json.dumps(response)
            return getattr(response, "content", str(response))
        except Exception:
            logger.exception("_invoke_model failed")
            return "Error: Model invocation failed"

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
                response = await self._invoke_model(
                    model, provider, enhanced_prompt, use_memory
                )
            except Exception:
                logger.exception("Model invocation failed for provider '%s'", provider)
                return f"Error: Model invocation failed for provider '{provider}'"

            # Best-effort cache store
            try:
                await self._cache_response(cache_key, provider, response)
            except Exception:
                logger.exception("Failed to cache response (non-fatal)")

            return response

        except Exception:
            logger.exception("invoke_with_rag unexpected failure")
            return "Error: Unexpected failure"

    async def multi_model_consensus(
        self, prompt: str, context: Dict[str, Any] = None, models: List[str] = None
    ) -> Dict[str, Any]:
        """Get consensus from multiple models for critical decisions."""
        models = models or ["openai", "anthropic", "gemini"]
        responses = {}

        for model in models:
            try:
                response = await self.invoke_with_rag(
                    prompt, model, context, use_memory=False
                )
                responses[model] = response
            except Exception as e:
                logger.exception("multi_model_consensus error for model '%s'", model)
                responses[model] = f"Error: {str(e)}"
        return responses

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

            # Create comprehensive prompt using dedent to normalize indentation
            full_prompt = textwrap.dedent(
                f"""
            {base_prompt}
            
            Document Title: {context.get('title', 'Unknown')}
            Domain: {domain}
            Pages: {context.get('metadata', {}).get('pages', 'Unknown')}
            
            Content:
            {content[:4000]}...
            
            Provide structured analysis with:
            1. Score (1-10)
            2. Strengths (3-5 points)
            3. Weaknesses (3-5 points)
            4. Specific recommendations
            5. Critical issues requiring attention
            
            Format as JSON with clear sections.
            """
            ).strip()

            # Invoke with RAG and return response
            response = await self.invoke_with_rag(
                full_prompt, context=context, use_memory=False
            )
            return response

        except Exception:
            logger.exception("domain_aware_review failed")
            return "Error: domain_aware_review failed"

    async def chain_of_thought_analysis(
        self, prompt: str, context: Dict[str, Any] = None
    ) -> str:
        """Perform step-by-step chain-of-thought analysis."""
        # Defensively handle None context
        context = context or {}

        cot_prompt = f"""
        Analyze this step-by-step using chain-of-thought reasoning:
        
        {prompt}
        
        Please think through this systematically:
        1. First, identify the key components to analyze
        2. Then, examine each component in detail
        3. Consider the relationships between components
        4. Evaluate strengths and weaknesses
        5. Synthesize findings into actionable insights
        
        Show your reasoning process clearly at each step.
        """

        return await self.invoke_with_rag(cot_prompt, context=context)

    def _build_rag_prompt(
        self, prompt: str, context: Dict[str, Any], rag_context: str
    ) -> str:
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

        # Build a context string whether or not additional context was provided
        context_str = (
            "\n".join(context_info)
            if context_info
            else "No additional context provided."
        )

        prompt_template = f"""
        Context Information:
        {context_str}

        Relevant Background Knowledge:
        {rag_context}

        Task:
        {prompt}

        Please provide a comprehensive response considering both the context and background knowledge.
        """

        # Remove leading indentation introduced by the function's indentation level
        return textwrap.dedent(prompt_template).strip()

    def _generate_cache_key(
        self, prompt: str, provider: str, context: Dict[str, Any]
    ) -> str:
        """Generate cache key for complex requests."""
        import hashlib

        key_data = {
            "prompt": prompt[:500],  # Truncate for key generation
            "provider": provider,
            "context": context,
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

    async def _cache_response(self, cache_key: str, provider: str, response: str) -> None:
        """Cache the response using the cache service."""
        try:
            await cache_service.set(cache_key, provider, response)
        except Exception:
            logger.exception("Failed to cache response")

    def cleanup_memory(self):
        """Clean up conversation memory."""
        self.memory.clear()


langchain_service = LangChainService()

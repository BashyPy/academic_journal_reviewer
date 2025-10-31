import json
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


class LangChainService:
    def __init__(self):
        self.models = self._initialize_models()
        self.embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", ".", " "]
        )
        self.memory = ConversationBufferWindowMemory(k=10, return_messages=True)
        self.vector_store = self._initialize_vector_store()
        self.domain_prompts = self._load_domain_specific_prompts()
        self.output_parsers = {"json": JsonOutputParser(), "string": StrOutputParser()}

    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize all LLM models with configurations."""
        return {
            "openai": ChatOpenAI(
                api_key=settings.OPENAI_API_KEY,
                model="gpt-4-turbo-preview",
                temperature=0.1,
                max_tokens=4000,
                request_timeout=60,
            ),
            "anthropic": ChatAnthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                model="claude-3-opus-20240229",
                temperature=0.1,
                max_tokens=4000,
            ),
            "gemini": ChatGoogleGenerativeAI(
                api_key=settings.GEMINI_API_KEY,
                model="gemini-pro",
                temperature=0.1,
                max_output_tokens=4000,
            ),
            "groq": ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model="llama3-70b-8192",
                temperature=0.1,
                max_tokens=4000,
            ),
        }

    def _initialize_vector_store(self) -> Optional[VectorStore]:
        """Initialize vector store for semantic search and retrieval."""
        try:
            return MongoDBAtlasVectorSearch(
                collection=mongodb_service.db["document_embeddings"],
                embedding=self.embeddings,
                index_name="vector_index",
                text_key="content",
                embedding_key="embedding",
            )
        except Exception:
            return None

    def _load_domain_specific_prompts(self) -> Dict[str, Dict[str, str]]:
        """Load domain-specific prompt templates."""
        return {
            "medical": {
                "methodology": "Analyze medical methodology: randomization, blinding, sample size, statistical power, IRB approval",
                "literature": "Evaluate medical literature: systematic reviews, clinical guidelines, evidence hierarchy",
                "ethics": "Assess medical ethics: informed consent, patient safety, data privacy",
                "clarity": "Review medical clarity: terminology, clinical significance, statistical reporting"
            },
            "psychology": {
                "methodology": "Analyze psychological methodology: validated instruments, reliability, validity, controls",
                "literature": "Evaluate psychology literature: theoretical frameworks, constructs, evidence",
                "ethics": "Assess psychological ethics: participant consent, harm prevention, debriefing",
                "clarity": "Review psychology clarity: operational definitions, statistical reporting"
            },
            "computer_science": {
                "methodology": "Analyze CS methodology: algorithm complexity, benchmarking, reproducibility",
                "literature": "Evaluate CS literature: state-of-art comparisons, technical novelty",
                "ethics": "Assess CS ethics: data privacy, algorithmic bias, transparency",
                "clarity": "Review CS clarity: code documentation, implementation details"
            },
            "biology": {
                "methodology": "Analyze biological methodology: experimental design, controls, statistical analysis",
                "literature": "Evaluate biology literature: evolutionary context, molecular mechanisms",
                "ethics": "Assess biological ethics: animal welfare, environmental impact",
                "clarity": "Review biology clarity: species identification, methodology description"
            },
            "physics": {
                "methodology": "Analyze physics methodology: experimental setup, measurement precision, error analysis",
                "literature": "Evaluate physics literature: theoretical foundations, experimental validation",
                "ethics": "Assess physics ethics: safety protocols, environmental considerations",
                "clarity": "Review physics clarity: mathematical notation, unit consistency"
            },
            "mathematics": {
                "methodology": "Analyze mathematical methodology: proof rigor, logical structure",
                "literature": "Evaluate mathematics literature: theorem citations, mathematical context",
                "ethics": "Assess mathematical ethics: attribution, originality",
                "clarity": "Review mathematics clarity: proof structure, notation consistency"
            },
            "economics": {
                "methodology": "Analyze economic methodology: econometric models, causal inference",
                "literature": "Evaluate economics literature: economic theory, empirical evidence",
                "ethics": "Assess economic ethics: data sources, conflicts of interest",
                "clarity": "Review economics clarity: model specification, variable definitions"
            },
            "law": {
                "methodology": "Analyze legal methodology: case law analysis, statutory interpretation",
                "literature": "Evaluate legal literature: precedent analysis, legal scholarship",
                "ethics": "Assess legal ethics: bias disclosure, conflict of interest",
                "clarity": "Review legal clarity: argument structure, legal reasoning"
            },
            "statistics": {
                "methodology": "Analyze statistical methodology: assumptions, model validation, power analysis",
                "literature": "Evaluate statistics literature: method comparisons, theoretical developments",
                "ethics": "Assess statistical ethics: data integrity, multiple testing",
                "clarity": "Review statistics clarity: notation, interpretation, visualization"
            },
            "bioinformatics": {
                "methodology": "Analyze bioinformatics methodology: algorithm validation, pipeline design",
                "literature": "Evaluate bioinformatics literature: tool comparisons, benchmarking",
                "ethics": "Assess bioinformatics ethics: data sharing, privacy protection",
                "clarity": "Review bioinformatics clarity: code availability, workflow documentation"
            }
        }

    async def create_document_embeddings(
        self, content: str, metadata: Dict[str, Any]
    ) -> List[str]:
        """Create and store document embeddings for semantic search."""
        if not self.vector_store:
            return []

        # Split document into chunks
        documents = self.text_splitter.create_documents([content], [metadata])

        # Store embeddings
        doc_ids = await self.vector_store.aadd_documents(documents)
        return doc_ids

    async def semantic_search(self, query: str, k: int = 5) -> List[Document]:
        """Perform semantic search on document embeddings."""
        if not self.vector_store:
            return []

        return await self.vector_store.asimilarity_search(query, k=k)

    async def invoke_with_rag(
        self,
        prompt: str,
        provider: str = None,
        context: Dict[str, Any] = None,
        use_memory: bool = True,
    ) -> str:
        """Invoke LLM with Retrieval-Augmented Generation."""
        provider = provider or settings.DEFAULT_LLM

        # Check cache first
        cache_key = self._generate_cache_key(prompt, provider, context)
        cached_response = await cache_service.get(cache_key, provider)
        if cached_response:
            return cached_response

        # Retrieve relevant context
        relevant_docs = await self.semantic_search(prompt)
        rag_context = "\n\n".join([doc.page_content for doc in relevant_docs[:3]])

        # Build enhanced prompt with RAG context
        enhanced_prompt = self._build_rag_prompt(prompt, context, rag_context)

        # Create conversation chain with memory
        model = self.models[provider]
        if use_memory:
            chain = ConversationChain(llm=model, memory=self.memory, verbose=False)
            response = await chain.apredict(input=enhanced_prompt)
        else:
            response = await model.ainvoke([HumanMessage(content=enhanced_prompt)])
            response = response.content

        # Cache response
        await cache_service.set(cache_key, provider, response)
        return response

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
                responses[model] = f"Error: {str(e)}"

        # Analyze consensus
        consensus_prompt = f"""
        Analyze these responses from different AI models and provide a consensus view:
        
        {json.dumps(responses, indent=2)}
        
        Provide:
        1. Areas of agreement
        2. Key differences
        3. Recommended consensus position
        4. Confidence level (1-10)
        """

        consensus = await self.invoke_with_rag(
            consensus_prompt, "openai", context, use_memory=False
        )

        return {"individual_responses": responses, "consensus_analysis": consensus}

    async def domain_aware_review(
        self, content: str, domain: str, review_type: str, context: Dict[str, Any]
    ) -> str:
        """Perform domain-aware review using specialized prompts."""
        # Get domain-specific prompt template
        domain_prompts = self.domain_prompts.get(domain, {})
        base_prompt = domain_prompts.get(review_type, "")

        if not base_prompt:
            base_prompt = f"Perform a {review_type} review of this {domain} manuscript."

        # Create comprehensive prompt
        full_prompt = f"""
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

        return await self.invoke_with_rag(
            full_prompt, context=context, use_memory=False
        )

    async def chain_of_thought_analysis(
        self, prompt: str, context: Dict[str, Any]
    ) -> str:
        """Perform step-by-step chain-of-thought analysis."""
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

        context_str = "\n".join(context_info)

        return f"""
        Context Information:
        {context_str}
        
        Relevant Background Knowledge:
        {rag_context}
        
        Task:
        {prompt}
        
        Please provide a comprehensive response considering both the context and background knowledge.
        """

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

    def cleanup_memory(self):
        """Clean up conversation memory."""
        self.memory.clear()


langchain_service = LangChainService()

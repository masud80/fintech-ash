import os
from typing import List, Dict, Any
import numpy as np
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
from firestore_vector_store import FirestoreVectorStore
from utils import get_openai_api_key, get_claude_api_key

load_dotenv()

class RAGManager:
    def __init__(self):
        """Initialize RAG manager with vector store and embedding model"""
        self.embedding_model = OpenAIEmbeddings(api_key=get_openai_api_key())
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Initialize LLM for compression
        self.llm = ChatAnthropic(
            model_name="claude-3-5-sonnet-latest",
            temperature=0.7,
            max_tokens_to_sample=4000,
            api_key=get_claude_api_key()
        )
        
        # Initialize Firestore vector store
        self.vector_store = FirestoreVectorStore()
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add documents to the vector store
        
        Args:
            documents: List of dictionaries containing document data
        """
        # Convert documents to LangChain Document objects and split into chunks
        docs = []
        for doc in documents:
            texts = self.text_splitter.split_text(doc["text"])
            for text in texts:
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": doc.get("source", "unknown"),
                        "date": doc.get("date", "unknown"),
                        "type": doc.get("type", "unknown")
                    }
                ))
        
        # Generate embeddings for all chunks
        texts = [doc.page_content for doc in docs]
        embeddings = self.embedding_model.embed_documents(texts)
        
        # Add to Firestore
        self.vector_store.add_documents(docs, embeddings)
    
    def retrieve_relevant_context(self, query: str, context_type: str = None) -> List[Document]:
        """Retrieve relevant documents from the vector store
        
        Args:
            query: The query string
            context_type: Optional filter for document type
            
        Returns:
            List of relevant documents
        """
        # Generate embedding for query
        query_embedding = self.embedding_model.embed_query(query)
        
        # Set up metadata filters if context_type is specified
        metadata_filters = {"type": context_type} if context_type else None
        
        # Search Firestore
        results = self.vector_store.search(
            query_embedding=query_embedding,
            limit=5,
            metadata_filters=metadata_filters
        )
        
        # Convert results to Document objects
        docs = []
        for result in results:
            docs.append(Document(
                page_content=result["content"],
                metadata=result["metadata"]
            ))
            
        return docs
    
    def format_context_for_prompt(self, docs: List[Document]) -> str:
        """Format retrieved documents into a prompt-friendly string
        
        Args:
            docs: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        context = "Relevant Context:\n\n"
        for i, doc in enumerate(docs, 1):
            context += f"Context {i}:\n"
            context += f"Source: {doc.metadata.get('source', 'Unknown')}\n"
            context += f"Date: {doc.metadata.get('date', 'Unknown')}\n"
            context += f"Type: {doc.metadata.get('type', 'Unknown')}\n"
            context += f"Content: {doc.page_content}\n\n"
        return context

# Initialize global RAG manager instance
rag_manager = RAGManager() 
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google.cloud.firestore_v1.vector import Vector
from google.cloud import firestore
from typing import List, Dict, Any
import numpy as np
from firebase.config import db      

class FirestoreVectorStore:
    def __init__(self, collection_name: str = "financial_data"):
        """Initialize Firestore vector store
        
        Args:
            collection_name: Name of the Firestore collection to use
        """
        self.db = db
        self.collection = self.db.collection(collection_name)
        
    def add_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]) -> None:
        """Add documents with their embeddings to Firestore
        
        Args:
            documents: List of document dictionaries containing content and metadata
            embeddings: List of embedding vectors for each document
        """
        batch = self.db.batch()
        
        for i, (doc, embedding) in enumerate(zip(documents, embeddings)):
            # Create document data
            doc_data = {
                "content": doc.get("text", ""),
                "embedding": embedding,
                "metadata": {
                    "source": doc.get("source", "unknown"),
                    "date": doc.get("date", "unknown"),
                    "type": doc.get("type", "unknown")
                },
                "timestamp": firestore.SERVER_TIMESTAMP
            }
            
            # Add to batch
            doc_ref = self.collection.document()
            batch.set(doc_ref, doc_data)
            
        # Commit the batch
        batch.commit()
        
    def search(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        distance_threshold: float = None,
        metadata_filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents
        
        Args:
            query_embedding: The embedding vector to search with
            limit: Maximum number of results to return
            distance_threshold: Maximum distance for results (None for no threshold)
            metadata_filters: Dictionary of metadata fields to filter by
            
        Returns:
            List of matching documents with their metadata and distances
        """
        # Start with base query
        query = self.collection
        
        # Apply metadata filters if provided
        if metadata_filters:
            for field, value in metadata_filters.items():
                query = query.where(f"metadata.{field}", "==", value)
        
        # Create vector query
        vector_query = query.find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_embedding),
            distance_measure=DistanceMeasure.COSINE,
            limit=limit,
            distance_threshold=distance_threshold
        )
        
        # Execute query and format results
        results = []
        for doc in vector_query.stream():
            doc_data = doc.to_dict()
            results.append({
                "id": doc.id,
                "content": doc_data["content"],
                "metadata": doc_data["metadata"],
                "distance": doc_data.get("distance", 0.0)
            })
            
        return results
        
    def delete_documents(self, document_ids: List[str]) -> None:
        """Delete documents by their IDs
        
        Args:
            document_ids: List of document IDs to delete
        """
        batch = self.db.batch()
        for doc_id in document_ids:
            doc_ref = self.collection.document(doc_id)
            batch.delete(doc_ref)
        batch.commit()
        
    def update_document(self, document_id: str, updates: Dict[str, Any]) -> None:
        """Update a document's fields
        
        Args:
            document_id: ID of the document to update
            updates: Dictionary of fields to update
        """
        doc_ref = self.collection.document(document_id)
        doc_ref.update(updates) 
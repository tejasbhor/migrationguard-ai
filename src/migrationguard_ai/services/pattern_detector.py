"""
Pattern detector for identifying recurring issues across signals.

This module implements pattern detection using:
- Sliding window analysis (2-minute windows)
- Similarity matching using Elasticsearch
- Pattern grouping using DBSCAN clustering
- Cross-merchant correlation
"""

from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib

from sklearn.cluster import DBSCAN
import numpy as np

from migrationguard_ai.core.schemas import Signal, Pattern
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.core.graceful_degradation import (
    PostgreSQLPatternMatcher,
    get_degradation_manager,
)
from migrationguard_ai.services.elasticsearch_client import ElasticsearchClient
from migrationguard_ai.services.elasticsearch_indices import (
    build_similarity_query,
    build_cross_merchant_query,
)

logger = get_logger(__name__)


class PatternDetector:
    """
    Detects patterns across signals using multiple techniques.
    
    Supports:
    - Temporal pattern analysis with sliding windows
    - Similarity matching for error messages
    - Clustering for grouping similar signals
    - Cross-merchant correlation
    """
    
    def __init__(self, es_client: ElasticsearchClient, db_session=None):
        """
        Initialize pattern detector.
        
        Args:
            es_client: Elasticsearch client for pattern storage and search
            db_session: Optional database session for PostgreSQL fallback
        """
        self.es_client = es_client
        self.db_session = db_session
        self.window_size_minutes = 2  # Sliding window size
        self.similarity_threshold = 0.7  # Minimum similarity score
        self.min_pattern_frequency = 3  # Minimum occurrences to form a pattern
        self.degradation_manager = get_degradation_manager()
        
        # Initialize PostgreSQL fallback if db_session provided
        self.pg_fallback = None
        if db_session:
            self.pg_fallback = PostgreSQLPatternMatcher(db_session)
        
    async def analyze_signals(
        self,
        signals: list[Signal],
        time_window_minutes: int = 120,
    ) -> list[Pattern]:
        """
        Analyze signals and detect patterns.
        
        Args:
            signals: List of signals to analyze
            time_window_minutes: Time window for pattern detection
            
        Returns:
            list[Pattern]: Detected patterns
        """
        if not signals:
            logger.debug("No signals to analyze")
            return []
        
        logger.info(
            "Analyzing signals for patterns",
            signal_count=len(signals),
            time_window=time_window_minutes,
        )
        
        patterns = []
        
        # Group signals by type for targeted analysis
        signals_by_type = self._group_signals_by_type(signals)
        
        for signal_type, type_signals in signals_by_type.items():
            if len(type_signals) < self.min_pattern_frequency:
                continue
            
            # Detect patterns for this signal type
            type_patterns = await self._detect_patterns_for_type(
                signal_type,
                type_signals,
                time_window_minutes,
            )
            patterns.extend(type_patterns)
        
        logger.info("Pattern detection completed", patterns_found=len(patterns))
        return patterns
    
    async def match_known_pattern(
        self,
        signal: Signal,
    ) -> Optional[Pattern]:
        """
        Match a signal against known patterns.
        
        Args:
            signal: Signal to match
            
        Returns:
            Optional[Pattern]: Matched pattern or None
        """
        try:
            # Build similarity query
            query = build_similarity_query(
                error_message=signal.error_message or "",
                error_code=signal.error_code,
                min_score=self.similarity_threshold,
            )
            
            # Search for similar patterns
            response = await self.es_client.search(
                index_name="patterns",
                query=query,
                size=1,
                sort=[{"confidence": {"order": "desc"}}],
            )
            
            hits = response.get("hits", {}).get("hits", [])
            if not hits:
                logger.debug("No matching pattern found", signal_id=signal.signal_id)
                return None
            
            # Convert hit to Pattern
            pattern_data = hits[0]["_source"]
            pattern = Pattern(**pattern_data)
            
            logger.info(
                "Pattern matched",
                signal_id=signal.signal_id,
                pattern_id=pattern.pattern_id,
                confidence=pattern.confidence,
            )
            
            # Mark Elasticsearch as healthy
            self.degradation_manager.set_degraded("elasticsearch", False)
            
            return pattern
            
        except Exception as e:
            logger.error(
                "Failed to match pattern in Elasticsearch",
                signal_id=signal.signal_id,
                error=str(e),
                exc_info=True,
            )
            
            # Mark Elasticsearch as degraded
            self.degradation_manager.set_degraded("elasticsearch", True)
            
            # Try PostgreSQL fallback
            if self.pg_fallback:
                logger.warning(
                    "Attempting PostgreSQL fallback for pattern matching",
                    signal_id=signal.signal_id,
                )
                try:
                    return await self.pg_fallback.match_pattern(signal)
                except Exception as fallback_error:
                    logger.error(
                        "PostgreSQL fallback also failed",
                        signal_id=signal.signal_id,
                        error=str(fallback_error),
                    )
            
            return None
    
    async def update_pattern(
        self,
        pattern_id: str,
        new_signals: list[str],
    ) -> Optional[Pattern]:
        """
        Update an existing pattern with new signal occurrences.
        
        Args:
            pattern_id: ID of pattern to update
            new_signals: List of new signal IDs
            
        Returns:
            Optional[Pattern]: Updated pattern or None if not found
        """
        try:
            # Get existing pattern
            pattern_data = await self.es_client.get_document(
                index_name="patterns",
                doc_id=pattern_id,
            )
            
            if not pattern_data:
                logger.warning("Pattern not found for update", pattern_id=pattern_id)
                return None
            
            # Update pattern data
            pattern_data["signal_ids"].extend(new_signals)
            pattern_data["frequency"] = len(pattern_data["signal_ids"])
            pattern_data["last_seen"] = datetime.utcnow().isoformat()
            pattern_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Recalculate confidence based on frequency
            pattern_data["confidence"] = min(
                0.95,
                0.5 + (pattern_data["frequency"] * 0.05),
            )
            
            # Update in Elasticsearch
            await self.es_client.update_document(
                index_name="patterns",
                doc_id=pattern_id,
                partial_doc=pattern_data,
            )
            
            pattern = Pattern(**pattern_data)
            
            logger.info(
                "Pattern updated",
                pattern_id=pattern_id,
                new_frequency=pattern.frequency,
                confidence=pattern.confidence,
            )
            
            return pattern
            
        except Exception as e:
            logger.error(
                "Failed to update pattern",
                pattern_id=pattern_id,
                error=str(e),
                exc_info=True,
            )
            return None
    
    def _group_signals_by_type(
        self,
        signals: list[Signal],
    ) -> dict[str, list[Signal]]:
        """Group signals by source type."""
        grouped = defaultdict(list)
        for signal in signals:
            grouped[signal.source].append(signal)
        return dict(grouped)
    
    async def _detect_patterns_for_type(
        self,
        signal_type: str,
        signals: list[Signal],
        time_window_minutes: int,
    ) -> list[Pattern]:
        """
        Detect patterns for a specific signal type.
        
        Args:
            signal_type: Type of signals
            signals: Signals of this type
            time_window_minutes: Time window for analysis
            
        Returns:
            list[Pattern]: Detected patterns
        """
        patterns = []
        
        # Group by error code
        by_error_code = self._group_by_error_code(signals)
        
        for error_code, code_signals in by_error_code.items():
            if len(code_signals) < self.min_pattern_frequency:
                continue
            
            # Check for cross-merchant pattern
            merchant_ids = list(set(s.merchant_id for s in code_signals))
            if len(merchant_ids) >= 2:
                pattern = await self._create_cross_merchant_pattern(
                    signal_type,
                    error_code,
                    code_signals,
                    merchant_ids,
                )
                if pattern:
                    patterns.append(pattern)
            
            # Check for temporal patterns (frequency-based)
            if len(code_signals) >= self.min_pattern_frequency:
                pattern = await self._create_frequency_pattern(
                    signal_type,
                    error_code,
                    code_signals,
                )
                if pattern:
                    patterns.append(pattern)
        
        # Cluster similar error messages (for signals without error codes)
        no_code_signals = [s for s in signals if not s.error_code]
        if len(no_code_signals) >= self.min_pattern_frequency:
            clustered_patterns = await self._cluster_by_similarity(
                signal_type,
                no_code_signals,
            )
            patterns.extend(clustered_patterns)
        
        return patterns
    
    def _group_by_error_code(
        self,
        signals: list[Signal],
    ) -> dict[str, list[Signal]]:
        """Group signals by error code."""
        grouped = defaultdict(list)
        for signal in signals:
            if signal.error_code:
                grouped[signal.error_code].append(signal)
        return dict(grouped)
    
    async def _create_cross_merchant_pattern(
        self,
        signal_type: str,
        error_code: str,
        signals: list[Signal],
        merchant_ids: list[str],
    ) -> Optional[Pattern]:
        """Create a cross-merchant pattern."""
        try:
            pattern_id = self._generate_pattern_id(
                f"cross_merchant_{signal_type}_{error_code}"
            )
            
            # Determine pattern type
            pattern_type = self._map_source_to_pattern_type(signal_type)
            
            # Calculate confidence based on merchant count and frequency
            confidence = min(
                0.95,
                0.6 + (len(merchant_ids) * 0.05) + (len(signals) * 0.02),
            )
            
            # Extract characteristics
            characteristics = {
                "error_code": error_code,
                "cross_merchant": True,
                "merchant_count": len(merchant_ids),
                "affected_resources": list(set(
                    s.affected_resource for s in signals if s.affected_resource
                )),
            }
            
            pattern = Pattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                confidence=confidence,
                signal_ids=[s.signal_id for s in signals],
                merchant_ids=merchant_ids,
                first_seen=min(s.timestamp for s in signals),
                last_seen=max(s.timestamp for s in signals),
                frequency=len(signals),
                characteristics=characteristics,
            )
            
            # Store in Elasticsearch
            await self.es_client.index_document(
                index_name="patterns",
                document=pattern.model_dump(mode="json"),
                doc_id=pattern_id,
            )
            
            logger.info(
                "Cross-merchant pattern created",
                pattern_id=pattern_id,
                merchant_count=len(merchant_ids),
                frequency=len(signals),
            )
            
            return pattern
            
        except Exception as e:
            logger.error(
                "Failed to create cross-merchant pattern",
                error=str(e),
                exc_info=True,
            )
            return None
    
    async def _create_frequency_pattern(
        self,
        signal_type: str,
        error_code: str,
        signals: list[Signal],
    ) -> Optional[Pattern]:
        """Create a frequency-based pattern."""
        try:
            pattern_id = self._generate_pattern_id(
                f"frequency_{signal_type}_{error_code}"
            )
            
            pattern_type = self._map_source_to_pattern_type(signal_type)
            
            # Calculate confidence based on frequency
            confidence = min(0.9, 0.5 + (len(signals) * 0.05))
            
            characteristics = {
                "error_code": error_code,
                "frequency_based": True,
                "time_span_minutes": (
                    max(s.timestamp for s in signals) - min(s.timestamp for s in signals)
                ).total_seconds() / 60,
            }
            
            pattern = Pattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                confidence=confidence,
                signal_ids=[s.signal_id for s in signals],
                merchant_ids=list(set(s.merchant_id for s in signals)),
                first_seen=min(s.timestamp for s in signals),
                last_seen=max(s.timestamp for s in signals),
                frequency=len(signals),
                characteristics=characteristics,
            )
            
            await self.es_client.index_document(
                index_name="patterns",
                document=pattern.model_dump(mode="json"),
                doc_id=pattern_id,
            )
            
            logger.info(
                "Frequency pattern created",
                pattern_id=pattern_id,
                frequency=len(signals),
            )
            
            return pattern
            
        except Exception as e:
            logger.error(
                "Failed to create frequency pattern",
                error=str(e),
                exc_info=True,
            )
            return None
    
    async def _cluster_by_similarity(
        self,
        signal_type: str,
        signals: list[Signal],
    ) -> list[Pattern]:
        """
        Cluster signals by error message similarity using DBSCAN.
        
        Args:
            signal_type: Type of signals
            signals: Signals to cluster
            
        Returns:
            list[Pattern]: Patterns from clusters
        """
        if len(signals) < self.min_pattern_frequency:
            return []
        
        try:
            # Extract error messages
            messages = [s.error_message or "" for s in signals]
            
            # Simple feature extraction: character n-grams
            # In production, use more sophisticated embeddings
            features = self._extract_text_features(messages)
            
            # DBSCAN clustering
            clustering = DBSCAN(eps=0.3, min_samples=self.min_pattern_frequency)
            labels = clustering.fit_predict(features)
            
            # Create patterns from clusters
            patterns = []
            for label in set(labels):
                if label == -1:  # Noise points
                    continue
                
                cluster_signals = [s for i, s in enumerate(signals) if labels[i] == label]
                if len(cluster_signals) >= self.min_pattern_frequency:
                    pattern = await self._create_cluster_pattern(
                        signal_type,
                        cluster_signals,
                        label,
                    )
                    if pattern:
                        patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            logger.error(
                "Failed to cluster signals",
                error=str(e),
                exc_info=True,
            )
            return []
    
    def _extract_text_features(self, messages: list[str]) -> np.ndarray:
        """
        Extract simple text features for clustering.
        
        In production, use embeddings from a language model.
        This is a simplified version using character n-grams.
        """
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        vectorizer = TfidfVectorizer(
            analyzer='char',
            ngram_range=(3, 5),
            max_features=100,
        )
        
        features = vectorizer.fit_transform(messages)
        return features.toarray()
    
    async def _create_cluster_pattern(
        self,
        signal_type: str,
        signals: list[Signal],
        cluster_label: int,
    ) -> Optional[Pattern]:
        """Create a pattern from a cluster of similar signals."""
        try:
            pattern_id = self._generate_pattern_id(
                f"cluster_{signal_type}_{cluster_label}_{len(signals)}"
            )
            
            pattern_type = self._map_source_to_pattern_type(signal_type)
            
            confidence = min(0.85, 0.5 + (len(signals) * 0.04))
            
            characteristics = {
                "cluster_based": True,
                "cluster_label": cluster_label,
                "similarity_threshold": self.similarity_threshold,
            }
            
            pattern = Pattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                confidence=confidence,
                signal_ids=[s.signal_id for s in signals],
                merchant_ids=list(set(s.merchant_id for s in signals)),
                first_seen=min(s.timestamp for s in signals),
                last_seen=max(s.timestamp for s in signals),
                frequency=len(signals),
                characteristics=characteristics,
            )
            
            await self.es_client.index_document(
                index_name="patterns",
                document=pattern.model_dump(mode="json"),
                doc_id=pattern_id,
            )
            
            logger.info(
                "Cluster pattern created",
                pattern_id=pattern_id,
                cluster_size=len(signals),
            )
            
            return pattern
            
        except Exception as e:
            logger.error(
                "Failed to create cluster pattern",
                error=str(e),
                exc_info=True,
            )
            return None
    
    def _generate_pattern_id(self, seed: str) -> str:
        """Generate a unique pattern ID from a seed string."""
        hash_obj = hashlib.sha256(seed.encode())
        return f"pattern_{hash_obj.hexdigest()[:16]}"
    
    def _map_source_to_pattern_type(self, source: str) -> str:
        """Map signal source to pattern type."""
        mapping = {
            "api_failure": "api_failure",
            "checkout_error": "checkout_issue",
            "webhook_failure": "webhook_problem",
            "support_ticket": "migration_stage_issue",
        }
        return mapping.get(source, "config_error")


# Singleton instance
_detector_instance: Optional[PatternDetector] = None


async def get_pattern_detector(es_client: ElasticsearchClient) -> PatternDetector:
    """
    Get or create the pattern detector singleton.
    
    Args:
        es_client: Elasticsearch client
        
    Returns:
        PatternDetector instance
    """
    global _detector_instance
    
    if _detector_instance is None:
        _detector_instance = PatternDetector(es_client)
    
    return _detector_instance

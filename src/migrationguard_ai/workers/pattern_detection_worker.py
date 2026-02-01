"""
Pattern detection worker.

This worker consumes signals from Kafka, detects patterns, and publishes
detected patterns to a separate topic for downstream processing.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta
from collections import deque

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.core.schemas import Signal, Pattern
from migrationguard_ai.services.kafka_consumer import KafkaConsumerWrapper
from migrationguard_ai.services.kafka_producer import KafkaProducerWrapper, get_kafka_producer
from migrationguard_ai.services.elasticsearch_client import get_elasticsearch_client
from migrationguard_ai.services.redis_client import get_redis_client
from migrationguard_ai.services.pattern_detector import get_pattern_detector
from migrationguard_ai.services.pattern_cache import get_pattern_cache
from migrationguard_ai.services.elasticsearch_indices import create_indices

logger = get_logger(__name__)


class PatternDetectionWorker:
    """
    Worker that consumes signals and detects patterns.
    
    Workflow:
    1. Consume signals from signals.normalized topic
    2. Buffer signals in a sliding window (2 minutes)
    3. Detect patterns using PatternDetector
    4. Store patterns in Elasticsearch and Redis
    5. Publish detected patterns to patterns.detected topic
    """
    
    def __init__(self):
        """Initialize pattern detection worker."""
        self.settings = get_settings()
        self.consumer: Optional[KafkaConsumerWrapper] = None
        self.producer: Optional[KafkaProducerWrapper] = None
        self.pattern_detector = None
        self.pattern_cache = None
        self.es_client = None
        self.redis_client = None
        
        # Sliding window for signal buffering
        self.window_size_minutes = 2
        self.signal_buffer: deque[Signal] = deque()
        self.last_analysis_time = datetime.utcnow()
        
        # Processing stats
        self.signals_processed = 0
        self.patterns_detected = 0
        self.errors = 0
        
        self._running = False
    
    async def start(self) -> None:
        """Start the pattern detection worker."""
        if self._running:
            logger.warning("Pattern detection worker already running")
            return
        
        try:
            logger.info("Starting pattern detection worker")
            
            # Initialize services
            await self._initialize_services()
            
            # Start consuming
            self._running = True
            await self._run()
            
        except Exception as e:
            logger.error("Failed to start pattern detection worker", error=str(e), exc_info=True)
            raise
    
    async def stop(self) -> None:
        """Stop the pattern detection worker."""
        if not self._running:
            logger.warning("Pattern detection worker not running")
            return
        
        try:
            logger.info("Stopping pattern detection worker")
            self._running = False
            
            # Stop consumer and producer
            if self.consumer:
                await self.consumer.stop()
            if self.producer:
                await self.producer.stop()
            
            # Close clients
            if self.es_client:
                await self.es_client.stop()
            if self.redis_client:
                await self.redis_client.stop()
            
            logger.info(
                "Pattern detection worker stopped",
                signals_processed=self.signals_processed,
                patterns_detected=self.patterns_detected,
                errors=self.errors,
            )
            
        except Exception as e:
            logger.error("Error stopping pattern detection worker", error=str(e))
            raise
    
    async def _initialize_services(self) -> None:
        """Initialize all required services."""
        # Initialize Elasticsearch
        self.es_client = await get_elasticsearch_client()
        
        # Create indices if they don't exist
        await create_indices(self.es_client)
        
        # Initialize Redis
        self.redis_client = await get_redis_client()
        
        # Initialize pattern detector
        self.pattern_detector = await get_pattern_detector(self.es_client)
        
        # Initialize pattern cache
        self.pattern_cache = await get_pattern_cache(self.redis_client, self.es_client)
        
        # Initialize Kafka producer
        self.producer = await get_kafka_producer()
        
        # Initialize Kafka consumer
        self.consumer = KafkaConsumerWrapper(
            topics=["signals.normalized"],
            group_id="pattern-detection-worker",
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
        )
        await self.consumer.start()
        
        logger.info("All services initialized")
    
    async def _run(self) -> None:
        """Main worker loop."""
        logger.info("Pattern detection worker running")
        
        # Schedule periodic pattern analysis
        analysis_task = asyncio.create_task(self._periodic_analysis())
        
        try:
            async for message in self.consumer.consume():
                if not self._running:
                    break
                
                try:
                    # Parse signal
                    signal = Signal(**message)
                    
                    # Add to buffer
                    self._add_to_buffer(signal)
                    
                    # Try to match against known patterns
                    await self._match_known_pattern(signal)
                    
                    self.signals_processed += 1
                    
                    if self.signals_processed % 100 == 0:
                        logger.info(
                            "Processing progress",
                            signals_processed=self.signals_processed,
                            patterns_detected=self.patterns_detected,
                            buffer_size=len(self.signal_buffer),
                        )
                    
                except Exception as e:
                    logger.error(
                        "Failed to process signal",
                        error=str(e),
                        exc_info=True,
                    )
                    self.errors += 1
        
        finally:
            # Cancel analysis task
            analysis_task.cancel()
            try:
                await analysis_task
            except asyncio.CancelledError:
                pass
    
    def _add_to_buffer(self, signal: Signal) -> None:
        """
        Add signal to sliding window buffer.
        
        Args:
            signal: Signal to add
        """
        self.signal_buffer.append(signal)
        
        # Remove old signals outside the window
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.window_size_minutes)
        while self.signal_buffer and self.signal_buffer[0].timestamp < cutoff_time:
            self.signal_buffer.popleft()
    
    async def _match_known_pattern(self, signal: Signal) -> None:
        """
        Try to match signal against known patterns.
        
        Args:
            signal: Signal to match
        """
        try:
            pattern = await self.pattern_detector.match_known_pattern(signal)
            
            if pattern:
                # Update pattern with new signal
                await self.pattern_detector.update_pattern(
                    pattern_id=pattern.pattern_id,
                    new_signals=[signal.signal_id],
                )
                
                # Invalidate cache
                await self.pattern_cache.invalidate_pattern(pattern.pattern_id)
                
                logger.info(
                    "Signal matched to known pattern",
                    signal_id=signal.signal_id,
                    pattern_id=pattern.pattern_id,
                )
        
        except Exception as e:
            logger.error(
                "Failed to match known pattern",
                signal_id=signal.signal_id,
                error=str(e),
            )
    
    async def _periodic_analysis(self) -> None:
        """Periodically analyze buffered signals for new patterns."""
        while self._running:
            try:
                # Wait for analysis interval (30 seconds)
                await asyncio.sleep(30)
                
                # Check if enough time has passed
                now = datetime.utcnow()
                if (now - self.last_analysis_time).total_seconds() < 60:
                    continue
                
                # Analyze buffered signals
                if len(self.signal_buffer) >= 3:  # Minimum signals for pattern
                    await self._analyze_buffer()
                
                self.last_analysis_time = now
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "Error in periodic analysis",
                    error=str(e),
                    exc_info=True,
                )
    
    async def _analyze_buffer(self) -> None:
        """Analyze buffered signals for patterns."""
        try:
            logger.info(
                "Analyzing signal buffer",
                buffer_size=len(self.signal_buffer),
            )
            
            # Convert deque to list
            signals = list(self.signal_buffer)
            
            # Detect patterns
            patterns = await self.pattern_detector.analyze_signals(
                signals=signals,
                time_window_minutes=self.window_size_minutes,
            )
            
            if patterns:
                logger.info(
                    "Patterns detected",
                    count=len(patterns),
                )
                
                # Store and publish each pattern
                for pattern in patterns:
                    await self._store_and_publish_pattern(pattern)
                
                self.patterns_detected += len(patterns)
        
        except Exception as e:
            logger.error(
                "Failed to analyze buffer",
                error=str(e),
                exc_info=True,
            )
    
    async def _store_and_publish_pattern(self, pattern: Pattern) -> None:
        """
        Store pattern and publish to Kafka.
        
        Args:
            pattern: Pattern to store and publish
        """
        try:
            # Store in cache (which also stores in Elasticsearch)
            await self.pattern_cache.store_pattern(pattern)
            
            # Publish to Kafka
            await self.producer.send(
                topic="patterns.detected",
                message=pattern.model_dump(mode="json"),
                key=pattern.pattern_id,
            )
            
            logger.info(
                "Pattern stored and published",
                pattern_id=pattern.pattern_id,
                pattern_type=pattern.pattern_type,
                confidence=pattern.confidence,
                frequency=pattern.frequency,
            )
        
        except Exception as e:
            logger.error(
                "Failed to store and publish pattern",
                pattern_id=pattern.pattern_id,
                error=str(e),
                exc_info=True,
            )


async def main():
    """Main entry point for the pattern detection worker."""
    worker = PatternDetectionWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())

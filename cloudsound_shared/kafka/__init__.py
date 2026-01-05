"""Kafka producer and consumer utilities."""
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import json
import structlog
from typing import Optional, Dict, Any, List
from cloudsound_shared.config.settings import app_settings

logger = structlog.get_logger(__name__)

class KafkaProducerClient:
    """Kafka producer client wrapper."""
    
    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.bootstrap_servers = bootstrap_servers or app_settings.kafka_bootstrap_servers
        self.producer: Optional[KafkaProducer] = None
    
    def connect(self) -> None:
        """Initialize Kafka producer."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,
            )
            logger.info("kafka_producer_connected", servers=self.bootstrap_servers)
        except Exception as e:
            logger.error("kafka_producer_connection_failed", error=str(e))
            raise
    
    def send(self, topic: str, value: Dict[Any, Any], key: Optional[str] = None) -> None:
        """Send message to Kafka topic."""
        if not self.producer:
            self.connect()
        
        try:
            future = self.producer.send(topic, value=value, key=key)
            future.get(timeout=10)  # Wait for confirmation
            logger.debug("kafka_message_sent", topic=topic, key=key)
        except KafkaError as e:
            logger.error("kafka_send_failed", topic=topic, error=str(e))
            raise
    
    def close(self) -> None:
        """Close producer connection."""
        if self.producer:
            self.producer.close()
            logger.info("kafka_producer_closed")

class KafkaConsumerClient:
    """Kafka consumer client wrapper."""
    
    def __init__(
        self,
        topics: List[str],
        group_id: str,
        bootstrap_servers: Optional[str] = None,
        auto_offset_reset: str = "earliest",
    ):
        self.topics = topics
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers or app_settings.kafka_bootstrap_servers
        self.auto_offset_reset = auto_offset_reset
        self.consumer: Optional[KafkaConsumer] = None
    
    def connect(self) -> None:
        """Initialize Kafka consumer."""
        try:
            self.consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=True,
            )
            logger.info(
                "kafka_consumer_connected",
                topics=self.topics,
                group_id=self.group_id,
                servers=self.bootstrap_servers,
            )
        except Exception as e:
            logger.error("kafka_consumer_connection_failed", error=str(e))
            raise
    
    def consume(self):
        """Consume messages from Kafka topics (generator)."""
        if not self.consumer:
            self.connect()
        
        try:
            for message in self.consumer:
                logger.debug(
                    "kafka_message_received",
                    topic=message.topic,
                    partition=message.partition,
                    offset=message.offset,
                    key=message.key,
                )
                yield message
        except Exception as e:
            logger.error("kafka_consume_error", error=str(e))
            raise
    
    def close(self) -> None:
        """Close consumer connection."""
        if self.consumer:
            self.consumer.close()
            logger.info("kafka_consumer_closed")


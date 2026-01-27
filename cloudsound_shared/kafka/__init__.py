"""Kafka producer and consumer utilities."""
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
import json
import structlog
import os
from typing import Optional, Dict, Any, List
from cloudsound_shared.config.settings import app_settings

logger = structlog.get_logger(__name__)

def _get_kafka_config() -> Dict[str, Any]:
    """Get Kafka configuration, supporting both regular Kafka and Azure Event Hubs."""
    config = {}
    
    # Check for Azure Event Hubs SASL configuration
    security_protocol = os.getenv('KAFKA_SECURITY_PROTOCOL', '').upper()
    sasl_mechanism = os.getenv('KAFKA_SASL_MECHANISM', '').upper()
    sasl_username = os.getenv('KAFKA_SASL_USERNAME', '')
    sasl_password = os.getenv('KAFKA_SASL_PASSWORD', '')
    
    # Azure Event Hubs uses SASL_SSL with PLAIN mechanism
    if security_protocol == 'SASL_SSL' and sasl_mechanism == 'PLAIN':
        config['security_protocol'] = 'SASL_SSL'
        config['sasl_mechanism'] = 'PLAIN'
        config['sasl_plain_username'] = sasl_username or '$ConnectionString'
        config['sasl_plain_password'] = sasl_password
        # Azure Event Hubs requires explicit API version
        config['api_version'] = (0, 10, 1)
        # SSL configuration for Event Hubs
        config['ssl_check_hostname'] = True
        config['ssl_cafile'] = None  # Use system CA certificates
        logger.info("kafka_config_azure_event_hubs", security_protocol=security_protocol)
    elif security_protocol or sasl_mechanism:
        # Other SASL configurations
        config['security_protocol'] = security_protocol
        if sasl_mechanism:
            config['sasl_mechanism'] = sasl_mechanism
        if sasl_username:
            config['sasl_plain_username'] = sasl_username
        if sasl_password:
            config['sasl_plain_password'] = sasl_password
    
    return config

class KafkaProducerClient:
    """Kafka producer client wrapper."""
    
    def __init__(self, bootstrap_servers: Optional[str] = None):
        self.bootstrap_servers = bootstrap_servers or app_settings.kafka_bootstrap_servers
        self.producer: Optional[KafkaProducer] = None
    
    def connect(self) -> None:
        """Initialize Kafka producer."""
        try:
            producer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'value_serializer': lambda v: json.dumps(v).encode('utf-8'),
                'key_serializer': lambda k: k.encode('utf-8') if k else None,
                'acks': 'all',  # Wait for all replicas
                'retries': 3,
                'max_in_flight_requests_per_connection': 1,
            }
            
            # Add SASL configuration if needed (for Azure Event Hubs)
            producer_config.update(_get_kafka_config())
            
            self.producer = KafkaProducer(**producer_config)
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
            consumer_config = {
                'bootstrap_servers': self.bootstrap_servers,
                'group_id': self.group_id,
                'value_deserializer': lambda m: json.loads(m.decode('utf-8')),
                'key_deserializer': lambda k: k.decode('utf-8') if k else None,
                'auto_offset_reset': self.auto_offset_reset,
                'enable_auto_commit': True,
            }
            
            # Add SASL configuration if needed (for Azure Event Hubs)
            consumer_config.update(_get_kafka_config())
            
            self.consumer = KafkaConsumer(*self.topics, **consumer_config)
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


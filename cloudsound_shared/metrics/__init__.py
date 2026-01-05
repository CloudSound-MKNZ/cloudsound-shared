"""Prometheus metrics utilities."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from typing import Optional
import time

# HTTP request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Business metrics
playback_events_total = Counter(
    'playback_events_total',
    'Total number of playback events',
    ['station_id', 'track_id']
)

kafka_messages_produced = Counter(
    'kafka_messages_produced_total',
    'Total number of Kafka messages produced',
    ['topic']
)

kafka_messages_consumed = Counter(
    'kafka_messages_consumed_total',
    'Total number of Kafka messages consumed',
    ['topic', 'group_id']
)

rabbitmq_messages_published = Counter(
    'rabbitmq_messages_published_total',
    'Total number of RabbitMQ messages published',
    ['queue']
)

rabbitmq_messages_consumed = Counter(
    'rabbitmq_messages_consumed_total',
    'Total number of RabbitMQ messages consumed',
    ['queue']
)

# System metrics
active_connections = Gauge(
    'active_connections',
    'Number of active database connections'
)

def get_metrics() -> str:
    """Get Prometheus metrics in text format."""
    return generate_latest(REGISTRY).decode('utf-8')


# Shared Backend Utilities

This directory contains shared code and utilities used across all backend microservices.

## Structure

- `db/` - Database connection pooling and migration utilities
- `models/` - Base model classes
- `kafka/` - Kafka producer/consumer utilities
- `rabbitmq/` - RabbitMQ connection utilities
- `storage/` - MinIO/S3 client utilities
- `logging/` - Structured logging configuration
- `metrics/` - Prometheus metrics utilities
- `health/` - Health check endpoint templates
- `middleware/` - Common middleware (error handling, correlation IDs)
- `config/` - Environment configuration management

## Usage

Services should import from this shared directory for common functionality. However, each service maintains its own dependencies and should not share code directly with other services (per microservices principles).


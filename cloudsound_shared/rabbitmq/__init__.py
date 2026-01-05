"""RabbitMQ connection utilities."""
import pika
import json
import structlog
from typing import Optional, Dict, Any, Callable
from cloudsound_shared.config.settings import app_settings

logger = structlog.get_logger(__name__)

class RabbitMQClient:
    """RabbitMQ client wrapper."""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        vhost: Optional[str] = None,
    ):
        self.host = host or app_settings.rabbitmq_host
        self.port = port or app_settings.rabbitmq_port
        self.user = user or app_settings.rabbitmq_user
        self.password = password or app_settings.rabbitmq_password
        self.vhost = vhost or app_settings.rabbitmq_vhost
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.channel.Channel] = None
    
    def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.vhost,
                credentials=credentials,
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            logger.info("rabbitmq_connected", host=self.host, port=self.port, vhost=self.vhost)
        except Exception as e:
            logger.error("rabbitmq_connection_failed", error=str(e))
            raise
    
    def declare_queue(self, queue_name: str, durable: bool = True) -> None:
        """Declare a queue."""
        if not self.channel:
            self.connect()
        
        self.channel.queue_declare(queue=queue_name, durable=durable)
        logger.debug("rabbitmq_queue_declared", queue=queue_name)
    
    def publish(self, queue_name: str, message: Dict[Any, Any], persistent: bool = True) -> None:
        """Publish message to queue."""
        if not self.channel:
            self.connect()
        
        properties = pika.BasicProperties(
            delivery_mode=2 if persistent else 1,  # 2 = persistent
        )
        
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message).encode('utf-8'),
            properties=properties,
        )
        logger.debug("rabbitmq_message_published", queue=queue_name)
    
    def consume(
        self,
        queue_name: str,
        callback: Callable[[Dict[Any, Any]], None],
        auto_ack: bool = False,
    ) -> None:
        """Consume messages from queue."""
        if not self.channel:
            self.connect()
        
        self.declare_queue(queue_name)
        
        def on_message(ch, method, properties, body):
            try:
                message = json.loads(body.decode('utf-8'))
                callback(message)
                if not auto_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                logger.error("rabbitmq_message_processing_failed", error=str(e))
                if not auto_ack:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message,
            auto_ack=auto_ack,
        )
        
        logger.info("rabbitmq_consuming", queue=queue_name)
        self.channel.start_consuming()
    
    def close(self) -> None:
        """Close connection."""
        if self.connection and not self.connection.is_closed:
            self.connection.close()
            logger.info("rabbitmq_connection_closed")


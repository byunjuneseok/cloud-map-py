"""Boto3 API caller with logging abstraction."""

import logging
from typing import Any, Dict, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError


class Boto3Caller:
    """Abstraction layer for boto3 API calls with logging."""
    
    def __init__(self, region: str, session: Optional[boto3.Session] = None):
        self.region = region
        self.session = session or boto3.Session()
        self.logger = logging.getLogger(__name__)
        self._clients: Dict[str, Any] = {}
    
    def get_client(self, service_name: str):
        """Get a boto3 client for the specified service."""
        if service_name not in self._clients:
            self._clients[service_name] = self.session.client(
                service_name, 
                region_name=self.region
            )
        return self._clients[service_name]
    
    def call_api(self, service: str, operation: str, **kwargs) -> Dict[str, Any]:
        """Make a boto3 API call with logging."""
        client = self.get_client(service)
        operation_method = getattr(client, operation)
        
        self.logger.info(
            f"Calling {service}.{operation} in region {self.region} with params: {kwargs}"
        )
        
        try:
            response = operation_method(**kwargs)
            self.logger.info(f"Successfully called {service}.{operation}")
            return response
        except (BotoCoreError, ClientError) as e:
            self.logger.error(f"Error calling {service}.{operation}: {e}")
            raise
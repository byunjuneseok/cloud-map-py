"""Interfaces and protocols for cloud map components."""

from abc import ABC, abstractmethod
from typing import List, Optional

from .models import VPC, Subnet, RouteTable, InternetGateway, EC2Instance


class NetworkDiscoverer(ABC):
    """Abstract base class for network discovery services."""
    
    @abstractmethod
    def discover_vpcs(self) -> List[VPC]:
        """Discover VPCs in the account."""
        pass
    
    @abstractmethod
    def discover_subnets(self, vpc_id: str) -> List[Subnet]:
        """Discover subnets for a given VPC."""
        pass
    
    @abstractmethod
    def discover_route_tables(self, vpc_id: str) -> List[RouteTable]:
        """Discover route tables for a given VPC."""
        pass
    
    @abstractmethod
    def discover_internet_gateways(self, vpc_id: str) -> List[InternetGateway]:
        """Discover internet gateways for a given VPC."""
        pass


class ComputeDiscoverer(ABC):
    """Abstract base class for compute resource discovery services."""
    
    @abstractmethod
    def discover_ec2_instances(self, subnet_id: Optional[str] = None) -> List[EC2Instance]:
        """Discover EC2 instances, optionally filtered by subnet."""
        pass
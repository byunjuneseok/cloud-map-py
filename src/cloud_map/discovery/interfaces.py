"""Interfaces and protocols for cloud map components."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..model.models import VPC, Subnet, RouteTable, InternetGateway, EC2Instance, LambdaFunction, Route53HostedZone, APIGateway, NATGateway, NetworkACL, SecurityGroup, RDSInstance, ElastiCacheCluster, ElastiCacheReplicationGroup, MSKCluster, RDSNode, ElastiCacheNode, MSKBrokerNode


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
    
    @abstractmethod
    def discover_nat_gateways(self, vpc_id: str) -> List[NATGateway]:
        """Discover NAT gateways for a given VPC."""
        pass
    
    @abstractmethod
    def discover_network_acls(self, vpc_id: str) -> List[NetworkACL]:
        """Discover Network ACLs for a given VPC."""
        pass
    
    @abstractmethod
    def discover_security_groups(self, vpc_id: str) -> List[SecurityGroup]:
        """Discover Security Groups for a given VPC."""
        pass


class ComputeDiscoverer(ABC):
    """Abstract base class for compute resource discovery services."""
    
    @abstractmethod
    def discover_ec2_instances(self, subnet_id: Optional[str] = None) -> List[EC2Instance]:
        """Discover EC2 instances, optionally filtered by subnet."""
        pass


class ServerlessDiscoverer(ABC):
    """Abstract base class for serverless resource discovery."""
    
    @abstractmethod
    def discover_lambda_functions(self, vpc_id: Optional[str] = None) -> List[LambdaFunction]:
        """Discover Lambda functions, optionally filtered by VPC."""
        pass


class NetworkUtilitiesDiscoverer(ABC):
    """Abstract base class for network utilities discovery."""
    
    @abstractmethod
    def discover_route53_zones(self, vpc_id: Optional[str] = None) -> List[Route53HostedZone]:
        """Discover Route53 hosted zones, optionally filtered by VPC."""
        pass
    
    @abstractmethod
    def discover_api_gateways(self, vpc_id: Optional[str] = None) -> List[APIGateway]:
        """Discover API Gateways, optionally filtered by VPC."""
        pass


class DatabaseDiscoverer(ABC):
    """Abstract base class for database resource discovery."""
    
    @abstractmethod
    def discover_rds_instances(self, vpc_id: Optional[str] = None) -> List[RDSInstance]:
        """Discover RDS database instances, optionally filtered by VPC."""
        pass
    
    @abstractmethod
    def discover_elasticache_clusters(self, vpc_id: Optional[str] = None) -> List[ElastiCacheCluster]:
        """Discover ElastiCache clusters, optionally filtered by VPC."""
        pass
    
    @abstractmethod
    def discover_elasticache_replication_groups(self, vpc_id: Optional[str] = None) -> List[ElastiCacheReplicationGroup]:
        """Discover ElastiCache replication groups, optionally filtered by VPC."""
        pass
    
    @abstractmethod
    def discover_msk_clusters(self, vpc_id: Optional[str] = None) -> List[MSKCluster]:
        """Discover MSK Kafka clusters, optionally filtered by VPC."""
        pass
"""Organization layer for networks and computing resources."""

from typing import List, Optional
from dataclasses import dataclass, field

from .models import VPC, Subnet, RouteTable, InternetGateway, EC2Instance, LambdaFunction


@dataclass
class NetworkTopology:
    """Organized network topology structure."""
    
    vpc: VPC
    subnets: List[Subnet] = field(default_factory=list)
    route_tables: List[RouteTable] = field(default_factory=list)
    internet_gateways: List[InternetGateway] = field(default_factory=list)
    ec2_instances: List[EC2Instance] = field(default_factory=list)
    lambda_functions: List[LambdaFunction] = field(default_factory=list)
    
    def get_subnet_by_id(self, subnet_id: str) -> Optional[Subnet]:
        """Get subnet by ID."""
        return next((subnet for subnet in self.subnets if subnet.resource_id == subnet_id), None)
    
    def get_instances_by_subnet(self, subnet_id: str) -> List[EC2Instance]:
        """Get EC2 instances in a specific subnet."""
        return [instance for instance in self.ec2_instances if instance.subnet_id == subnet_id]
    
    def get_lambda_functions_by_subnet(self, subnet_id: str) -> List[LambdaFunction]:
        """Get Lambda functions in a specific subnet."""
        return [func for func in self.lambda_functions if subnet_id in func.subnet_ids]
    
    def get_public_subnets(self) -> List[Subnet]:
        """Get subnets that map public IPs on launch."""
        return [subnet for subnet in self.subnets if subnet.map_public_ip_on_launch]
    
    def get_private_subnets(self) -> List[Subnet]:
        """Get subnets that don't map public IPs on launch."""
        return [subnet for subnet in self.subnets if not subnet.map_public_ip_on_launch]


@dataclass
class AccountTopology:
    """Account-level topology organization."""
    
    region: str
    vpcs: List[NetworkTopology] = field(default_factory=list)
    
    def get_vpc_topology(self, vpc_id: str) -> Optional[NetworkTopology]:
        """Get VPC topology by VPC ID."""
        return next((vpc_topo for vpc_topo in self.vpcs if vpc_topo.vpc.resource_id == vpc_id), None)
    
    def get_all_instances(self) -> List[EC2Instance]:
        """Get all EC2 instances across all VPCs."""
        instances = []
        for vpc_topology in self.vpcs:
            instances.extend(vpc_topology.ec2_instances)
        return instances
    
    def get_all_subnets(self) -> List[Subnet]:
        """Get all subnets across all VPCs."""
        subnets = []
        for vpc_topology in self.vpcs:
            subnets.extend(vpc_topology.subnets)
        return subnets


class ResourceOrganizer:
    """Organizes discovered resources into structured topology."""
    
    def organize_network_topology(
        self,
        vpcs: List[VPC],
        subnets: List[Subnet],
        route_tables: List[RouteTable],
        internet_gateways: List[InternetGateway],
        ec2_instances: List[EC2Instance],
        lambda_functions: Optional[List[LambdaFunction]] = None
    ) -> List[NetworkTopology]:
        """Organize resources into VPC-level topologies."""
        
        topologies = []
        lambda_functions = lambda_functions or []
        
        for vpc in vpcs:
            vpc_subnets = [subnet for subnet in subnets if subnet.vpc_id == vpc.resource_id]
            vpc_route_tables = [rt for rt in route_tables if rt.vpc_id == vpc.resource_id]
            vpc_gateways = [igw for igw in internet_gateways if igw.vpc_id == vpc.resource_id]
            vpc_instances = [instance for instance in ec2_instances if instance.vpc_id == vpc.resource_id]
            
            vpc_lambda_functions = []
            for func in lambda_functions:
                if func.vpc_config and any(subnet.vpc_id == vpc.resource_id for subnet in vpc_subnets 
                                         if subnet.resource_id in func.subnet_ids):
                    vpc_lambda_functions.append(func)
            
            topology = NetworkTopology(
                vpc=vpc,
                subnets=vpc_subnets,
                route_tables=vpc_route_tables,
                internet_gateways=vpc_gateways,
                ec2_instances=vpc_instances,
                lambda_functions=vpc_lambda_functions
            )
            topologies.append(topology)
        
        return topologies
    
    def create_account_topology(
        self,
        region: str,
        network_topologies: List[NetworkTopology]
    ) -> AccountTopology:
        """Create account-level topology."""
        
        return AccountTopology(
            region=region,
            vpcs=network_topologies
        )
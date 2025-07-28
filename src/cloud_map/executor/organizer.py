"""Organization layer for networks and computing resources."""

from typing import List, Optional
from dataclasses import dataclass, field

from ..model.models import VPC, Subnet, RouteTable, InternetGateway, EC2Instance, LambdaFunction, Route53HostedZone, APIGateway, NATGateway, NetworkACL, SecurityGroup, RDSInstance, ElastiCacheCluster, ElastiCacheReplicationGroup, MSKCluster, RDSNode, ElastiCacheNode, MSKBrokerNode


@dataclass
class NetworkTopology:
    """Organized network topology structure."""
    
    vpc: VPC
    subnets: List[Subnet] = field(default_factory=list)
    route_tables: List[RouteTable] = field(default_factory=list)
    internet_gateways: List[InternetGateway] = field(default_factory=list)
    nat_gateways: List[NATGateway] = field(default_factory=list)
    network_acls: List[NetworkACL] = field(default_factory=list)
    security_groups: List[SecurityGroup] = field(default_factory=list)
    ec2_instances: List[EC2Instance] = field(default_factory=list)
    lambda_functions: List[LambdaFunction] = field(default_factory=list)
    route53_zones: List[Route53HostedZone] = field(default_factory=list)
    api_gateways: List[APIGateway] = field(default_factory=list)
    rds_instances: List[RDSInstance] = field(default_factory=list)
    elasticache_clusters: List[ElastiCacheCluster] = field(default_factory=list)
    elasticache_replication_groups: List[ElastiCacheReplicationGroup] = field(default_factory=list)
    msk_clusters: List[MSKCluster] = field(default_factory=list)
    
    def get_subnet_by_id(self, subnet_id: str) -> Optional[Subnet]:
        """Get subnet by ID."""
        return next((subnet for subnet in self.subnets if subnet.resource_id == subnet_id), None)
    
    def get_instances_by_subnet(self, subnet_id: str) -> List[EC2Instance]:
        """Get EC2 instances in a specific subnet."""
        return [instance for instance in self.ec2_instances if instance.subnet_id == subnet_id]
    
    def get_lambda_functions_by_subnet(self, subnet_id: str) -> List[LambdaFunction]:
        """Get Lambda functions in a specific subnet."""
        return [func for func in self.lambda_functions if subnet_id in func.subnet_ids]
    
    def get_rds_nodes_by_subnet(self, subnet_id: str) -> List['RDSNode']:
        """Get individual RDS nodes in this specific subnet."""
        nodes = []
        for rds_instance in self.rds_instances:
            for node in rds_instance.rds_nodes:
                if node.subnet_id == subnet_id:
                    nodes.append(node)
        return nodes
    
    def get_rds_instances_by_subnet(self, subnet_id: str) -> List['RDSInstance']:
        """Get RDS instances that have subnet groups containing this subnet."""
        # For backward compatibility - show RDS instances in all subnets of their AZ
        subnet = self.get_subnet_by_id(subnet_id)
        if not subnet:
            return []
        
        return [rds for rds in self.rds_instances 
                if rds.availability_zone == subnet.availability_zone]
    
    def get_elasticache_nodes_by_subnet(self, subnet_id: str) -> List['ElastiCacheNode']:
        """Get individual ElastiCache nodes in this specific subnet."""
        nodes = []
        
        # Get nodes from standalone clusters
        for cluster in self.elasticache_clusters:
            for node in cluster.elasticache_nodes:
                if node.subnet_id == subnet_id:
                    nodes.append(node)
        
        # Get nodes from replication groups
        for replication_group in self.elasticache_replication_groups:
            for node in replication_group.elasticache_nodes:
                if node.subnet_id == subnet_id:
                    nodes.append(node)
        
        return nodes
    
    def get_elasticache_clusters_by_subnet(self, subnet_id: str) -> List['ElastiCacheCluster']:
        """Get ElastiCache clusters that are in subnet groups containing this subnet."""
        subnet = self.get_subnet_by_id(subnet_id)
        if not subnet:
            return []
        
        # ElastiCache clusters with specific AZ preference or subnet groups
        return [cache for cache in self.elasticache_clusters 
                if (cache.preferred_availability_zone == subnet.availability_zone or
                    cache.cache_subnet_group_name)]
    
    def get_elasticache_replication_groups_by_subnet(self, subnet_id: str) -> List['ElastiCacheReplicationGroup']:
        """Get ElastiCache replication groups that span this subnet."""
        # Replication groups typically span multiple AZs, so show in all subnets
        return self.elasticache_replication_groups
    
    def get_msk_broker_nodes_by_subnet(self, subnet_id: str) -> List['MSKBrokerNode']:
        """Get individual MSK broker nodes in this specific subnet."""
        nodes = []
        for cluster in self.msk_clusters:
            for node in cluster.broker_nodes:
                if node.subnet_id == subnet_id:
                    nodes.append(node)
        return nodes
    
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
        nat_gateways: List[NATGateway],
        network_acls: List[NetworkACL],
        security_groups: List[SecurityGroup],
        ec2_instances: List[EC2Instance],
        lambda_functions: Optional[List[LambdaFunction]] = None,
        route53_zones: Optional[List[Route53HostedZone]] = None,
        api_gateways: Optional[List[APIGateway]] = None,
        rds_instances: Optional[List[RDSInstance]] = None,
        elasticache_clusters: Optional[List[ElastiCacheCluster]] = None,
        elasticache_replication_groups: Optional[List[ElastiCacheReplicationGroup]] = None,
        msk_clusters: Optional[List[MSKCluster]] = None
    ) -> List[NetworkTopology]:
        """Organize resources into VPC-level topologies."""
        
        topologies = []
        lambda_functions = lambda_functions or []
        route53_zones = route53_zones or []
        api_gateways = api_gateways or []
        rds_instances = rds_instances or []
        elasticache_clusters = elasticache_clusters or []
        elasticache_replication_groups = elasticache_replication_groups or []
        msk_clusters = msk_clusters or []
        
        for vpc in vpcs:
            vpc_subnets = [subnet for subnet in subnets if subnet.vpc_id == vpc.resource_id]
            vpc_route_tables = [rt for rt in route_tables if rt.vpc_id == vpc.resource_id]
            vpc_gateways = [igw for igw in internet_gateways if igw.vpc_id == vpc.resource_id]
            vpc_nat_gateways = [nat for nat in nat_gateways if nat.vpc_id == vpc.resource_id]
            vpc_network_acls = [acl for acl in network_acls if acl.vpc_id == vpc.resource_id]
            vpc_security_groups = [sg for sg in security_groups if sg.vpc_id == vpc.resource_id]
            vpc_instances = [instance for instance in ec2_instances if instance.vpc_id == vpc.resource_id]
            
            vpc_lambda_functions = []
            for func in lambda_functions:
                if func.vpc_config and any(subnet.vpc_id == vpc.resource_id for subnet in vpc_subnets 
                                         if subnet.resource_id in func.subnet_ids):
                    vpc_lambda_functions.append(func)
            
            vpc_route53_zones = [zone for zone in route53_zones if vpc.resource_id in zone.vpc_associations]
            vpc_rds_instances = [rds for rds in rds_instances if rds.vpc_id == vpc.resource_id]
            vpc_elasticache_clusters = [cache for cache in elasticache_clusters if cache.vpc_id == vpc.resource_id]
            vpc_elasticache_replication_groups = [rg for rg in elasticache_replication_groups if rg.vpc_id == vpc.resource_id]
            vpc_msk_clusters = [msk for msk in msk_clusters if msk.vpc_id == vpc.resource_id]
            
            topology = NetworkTopology(
                vpc=vpc,
                subnets=vpc_subnets,
                route_tables=vpc_route_tables,
                internet_gateways=vpc_gateways,
                nat_gateways=vpc_nat_gateways,
                network_acls=vpc_network_acls,
                security_groups=vpc_security_groups,
                ec2_instances=vpc_instances,
                lambda_functions=vpc_lambda_functions,
                route53_zones=vpc_route53_zones,
                api_gateways=api_gateways,
                rds_instances=vpc_rds_instances,
                elasticache_clusters=vpc_elasticache_clusters,
                elasticache_replication_groups=vpc_elasticache_replication_groups,
                msk_clusters=vpc_msk_clusters
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
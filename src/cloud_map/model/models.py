"""Resource models for cloud infrastructure components."""

from abc import ABC
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class BaseResource(ABC):
    """Base class for all AWS resources."""
    
    resource_id: str
    resource_type: str
    region: str
    tags: Dict[str, str]
    
    def __post_init__(self):
        if hasattr(self, 'name') and not self.name and 'Name' in self.tags:
            self.name = self.tags['Name']


@dataclass
class VPC(BaseResource):
    """VPC resource model."""
    
    cidr_block: str
    state: str
    is_default: bool
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "vpc"


@dataclass
class Subnet(BaseResource):
    """Subnet resource model."""
    
    vpc_id: str
    cidr_block: str
    availability_zone: str
    state: str
    map_public_ip_on_launch: bool
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "subnet"


@dataclass
class RouteTable(BaseResource):
    """Route table resource model."""
    
    vpc_id: str
    routes: List[Dict[str, str]]
    subnet_associations: List[str]
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "route_table"


@dataclass
class InternetGateway(BaseResource):
    """Internet gateway resource model."""
    
    vpc_id: Optional[str]
    state: str
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "internet_gateway"


@dataclass
class EC2Instance(BaseResource):
    """EC2 instance resource model."""
    
    instance_type: str
    state: str
    vpc_id: str
    subnet_id: str
    private_ip: str
    security_groups: List[str]
    public_ip: Optional[str] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "ec2_instance"


@dataclass
class LambdaFunction(BaseResource):
    """Lambda function resource model."""
    
    function_name: str
    runtime: str
    state: str
    subnet_ids: List[str]
    security_group_ids: List[str]
    vpc_config: Optional[Dict[str, str]] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "lambda_function"


@dataclass
class Route53HostedZone(BaseResource):
    """Route53 hosted zone resource model."""
    
    zone_name: str
    zone_id: str
    private_zone: bool
    record_count: int
    vpc_associations: List[str]
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "route53_hosted_zone"


@dataclass
class APIGateway(BaseResource):
    """API Gateway resource model."""
    
    api_name: str
    api_type: str
    protocol_type: str
    endpoint_type: str
    vpc_links: List[str]
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "api_gateway"


@dataclass
class NATGateway(BaseResource):
    """NAT Gateway resource model."""
    
    vpc_id: str
    subnet_id: str
    state: str
    nat_gateway_type: str
    connectivity_type: str
    allocation_id: Optional[str] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "nat_gateway"


@dataclass
class NetworkACL(BaseResource):
    """Network ACL resource model."""
    
    vpc_id: str
    is_default: bool
    subnet_associations: List[str]
    entries: List[Dict[str, str]]
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "network_acl"


@dataclass
class SecurityGroup(BaseResource):
    """Security Group resource model."""
    
    vpc_id: str
    group_name: str
    description: str
    inbound_rules: List[Dict[str, str]]
    outbound_rules: List[Dict[str, str]]
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "security_group"


@dataclass
class RDSInstance(BaseResource):
    """RDS database instance resource model."""
    
    db_instance_identifier: str
    db_instance_class: str
    engine: str
    engine_version: str
    db_name: Optional[str]
    endpoint: Optional[str]
    port: int
    vpc_id: Optional[str]
    subnet_group_name: Optional[str]
    availability_zone: str
    multi_az: bool
    publicly_accessible: bool
    storage_type: str
    allocated_storage: int
    storage_encrypted: bool
    db_instance_status: str
    read_replica_source: Optional[str] = None
    read_replica_db_instance_identifiers: List[str] = None
    rds_nodes: List['RDSNode'] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "rds_instance"
        if self.read_replica_db_instance_identifiers is None:
            self.read_replica_db_instance_identifiers = []
        if self.rds_nodes is None:
            self.rds_nodes = []


@dataclass
class ElastiCacheCluster(BaseResource):
    """ElastiCache cluster resource model."""
    
    cache_cluster_id: str
    cache_node_type: str
    engine: str
    engine_version: str
    cache_cluster_status: str
    num_cache_nodes: int
    preferred_availability_zone: Optional[str]
    cache_subnet_group_name: Optional[str]
    vpc_id: Optional[str]
    security_group_ids: List[str]
    port: int
    parameter_group_name: str
    cache_nodes: List[Dict[str, str]]
    elasticache_nodes: List['ElastiCacheNode'] = None
    replication_group_id: Optional[str] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "elasticache_cluster"
        if self.elasticache_nodes is None:
            self.elasticache_nodes = []


@dataclass
class ElastiCacheReplicationGroup(BaseResource):
    """ElastiCache replication group resource model."""
    
    replication_group_id: str
    description: str
    status: str
    primary_cluster_id: Optional[str]
    member_clusters: List[str]
    node_groups: List[Dict[str, str]]
    cache_node_type: str
    engine: str
    engine_version: str
    cache_subnet_group_name: Optional[str]
    vpc_id: Optional[str]
    security_group_ids: List[str]
    port: int
    multi_az: str
    automatic_failover: str
    elasticache_nodes: List['ElastiCacheNode'] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "elasticache_replication_group"
        if self.elasticache_nodes is None:
            self.elasticache_nodes = []


@dataclass
class RDSNode(BaseResource):
    """Individual RDS node (for Multi-AZ or read replicas)."""
    
    db_instance_identifier: str
    parent_cluster_id: str
    node_type: str  # primary, replica, standby
    availability_zone: str
    subnet_id: str
    endpoint: Optional[str]
    port: int
    status: str
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "rds_node"


@dataclass
class ElastiCacheNode(BaseResource):
    """Individual ElastiCache node."""
    
    cache_node_id: str
    cache_cluster_id: str
    cache_node_type: str
    cache_node_status: str
    availability_zone: str
    subnet_id: str
    endpoint: Optional[str]
    port: int
    parameter_group_status: str
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "elasticache_node"


@dataclass
class MSKBrokerNode(BaseResource):
    """Individual MSK Kafka broker node."""
    
    broker_id: str
    cluster_arn: str
    instance_type: str
    availability_zone: str
    subnet_id: str
    client_subnet: str
    endpoint: Optional[str]
    client_vpc_ip_address: str
    status: str
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "msk_broker_node"


@dataclass
class MSKCluster(BaseResource):
    """Amazon MSK (Kafka) cluster resource model."""
    
    cluster_name: str
    cluster_arn: str
    kafka_version: str
    number_of_broker_nodes: int
    instance_type: str
    state: str
    creation_time: str
    current_version: str
    broker_node_group_info: Dict[str, str]
    subnet_ids: List[str]
    security_group_ids: List[str]
    vpc_id: Optional[str]
    encryption_info: Dict[str, str]
    client_authentication: Dict[str, str]
    logging_info: Dict[str, str]
    broker_nodes: List[MSKBrokerNode] = None
    zookeeper_connect_string: Optional[str] = None
    bootstrap_broker_string: Optional[str] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.resource_type = "msk_cluster"
        if self.broker_nodes is None:
            self.broker_nodes = []
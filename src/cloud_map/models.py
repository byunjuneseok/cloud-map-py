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
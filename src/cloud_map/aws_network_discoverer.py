"""AWS network discovery implementation."""

from typing import List, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .interfaces import NetworkDiscoverer
from .models import VPC, Subnet, RouteTable, InternetGateway


class AWSNetworkDiscoverer(NetworkDiscoverer):
    """AWS implementation of network discovery."""
    
    def __init__(self, region: str = 'us-east-1', session: Optional[boto3.Session] = None):
        self.region = region
        self.session = session or boto3.Session()
        self.ec2_client = self.session.client('ec2', region_name=region)
    
    def discover_vpcs(self) -> List[VPC]:
        """Discover VPCs in the account."""
        try:
            response = self.ec2_client.describe_vpcs()
            vpcs = []
            
            for vpc_data in response['Vpcs']:
                tags = {tag['Key']: tag['Value'] for tag in vpc_data.get('Tags', [])}
                
                vpc = VPC(
                    resource_id=vpc_data['VpcId'],
                    resource_type='vpc',
                    region=self.region,
                    tags=tags,
                    cidr_block=vpc_data['CidrBlock'],
                    state=vpc_data['State'],
                    is_default=vpc_data.get('IsDefault', False)
                )
                vpcs.append(vpc)
            
            return vpcs
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover VPCs: {e}")
    
    def discover_subnets(self, vpc_id: str) -> List[Subnet]:
        """Discover subnets for a given VPC."""
        try:
            response = self.ec2_client.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            subnets = []
            
            for subnet_data in response['Subnets']:
                tags = {tag['Key']: tag['Value'] for tag in subnet_data.get('Tags', [])}
                
                subnet = Subnet(
                    resource_id=subnet_data['SubnetId'],
                    resource_type='subnet',
                    region=self.region,
                    tags=tags,
                    vpc_id=subnet_data['VpcId'],
                    cidr_block=subnet_data['CidrBlock'],
                    availability_zone=subnet_data['AvailabilityZone'],
                    state=subnet_data['State'],
                    map_public_ip_on_launch=subnet_data.get('MapPublicIpOnLaunch', False)
                )
                subnets.append(subnet)
            
            return subnets
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover subnets for VPC {vpc_id}: {e}")
    
    def discover_route_tables(self, vpc_id: str) -> List[RouteTable]:
        """Discover route tables for a given VPC."""
        try:
            response = self.ec2_client.describe_route_tables(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            route_tables = []
            
            for rt_data in response['RouteTables']:
                tags = {tag['Key']: tag['Value'] for tag in rt_data.get('Tags', [])}
                
                routes = []
                for route in rt_data.get('Routes', []):
                    route_info = {
                        'destination': route.get('DestinationCidrBlock', ''),
                        'gateway_id': route.get('GatewayId', ''),
                        'state': route.get('State', '')
                    }
                    routes.append(route_info)
                
                subnet_associations = [
                    assoc['SubnetId'] for assoc in rt_data.get('Associations', [])
                    if 'SubnetId' in assoc
                ]
                
                route_table = RouteTable(
                    resource_id=rt_data['RouteTableId'],
                    resource_type='route_table',
                    region=self.region,
                    tags=tags,
                    vpc_id=rt_data['VpcId'],
                    routes=routes,
                    subnet_associations=subnet_associations
                )
                route_tables.append(route_table)
            
            return route_tables
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover route tables for VPC {vpc_id}: {e}")
    
    def discover_internet_gateways(self, vpc_id: str) -> List[InternetGateway]:
        """Discover internet gateways for a given VPC."""
        try:
            response = self.ec2_client.describe_internet_gateways(
                Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
            )
            gateways = []
            
            for igw_data in response['InternetGateways']:
                tags = {tag['Key']: tag['Value'] for tag in igw_data.get('Tags', [])}
                
                attachments = igw_data.get('Attachments', [])
                attached_vpc_id = attachments[0]['VpcId'] if attachments else None
                state = attachments[0]['State'] if attachments else 'detached'
                
                gateway = InternetGateway(
                    resource_id=igw_data['InternetGatewayId'],
                    resource_type='internet_gateway',
                    region=self.region,
                    tags=tags,
                    vpc_id=attached_vpc_id,
                    state=state
                )
                gateways.append(gateway)
            
            return gateways
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover internet gateways for VPC {vpc_id}: {e}")
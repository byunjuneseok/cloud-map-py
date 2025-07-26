"""AWS network discovery implementation."""

from typing import List, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .interfaces import NetworkDiscoverer
from ..model.models import VPC, Subnet, RouteTable, InternetGateway, NATGateway, NetworkACL, SecurityGroup
from .boto3_caller import Boto3Caller


class AWSNetworkDiscoverer(NetworkDiscoverer):
    """AWS implementation of network discovery."""
    
    def __init__(self, region: str = 'us-east-1', session: Optional[boto3.Session] = None):
        self.region = region
        self.boto3_caller = Boto3Caller(region, session)
    
    def discover_vpcs(self) -> List[VPC]:
        """Discover VPCs in the account."""
        try:
            response = self.boto3_caller.call_api('ec2', 'describe_vpcs')
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
            response = self.boto3_caller.call_api(
                'ec2', 'describe_subnets',
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
            response = self.boto3_caller.call_api(
                'ec2', 'describe_route_tables',
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
            response = self.boto3_caller.call_api(
                'ec2', 'describe_internet_gateways',
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
    
    def discover_nat_gateways(self, vpc_id: str) -> List[NATGateway]:
        """Discover NAT gateways for a given VPC."""
        try:
            response = self.boto3_caller.call_api(
                'ec2', 'describe_nat_gateways',
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            nat_gateways = []
            
            for nat_data in response['NatGateways']:
                tags = {tag['Key']: tag['Value'] for tag in nat_data.get('Tags', [])}
                
                nat_gateway = NATGateway(
                    resource_id=nat_data['NatGatewayId'],
                    resource_type='nat_gateway',
                    region=self.region,
                    tags=tags,
                    vpc_id=nat_data['VpcId'],
                    subnet_id=nat_data['SubnetId'],
                    state=nat_data['State'],
                    nat_gateway_type=nat_data.get('NatGatewayType', 'Gateway'),
                    connectivity_type=nat_data.get('ConnectivityType', 'public'),
                    allocation_id=nat_data.get('NatGatewayAddresses', [{}])[0].get('AllocationId')
                )
                nat_gateways.append(nat_gateway)
            
            return nat_gateways
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover NAT gateways for VPC {vpc_id}: {e}")
    
    def discover_network_acls(self, vpc_id: str) -> List[NetworkACL]:
        """Discover Network ACLs for a given VPC."""
        try:
            response = self.boto3_caller.call_api(
                'ec2', 'describe_network_acls',
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            network_acls = []
            
            for acl_data in response['NetworkAcls']:
                tags = {tag['Key']: tag['Value'] for tag in acl_data.get('Tags', [])}
                
                entries = []
                for entry in acl_data.get('Entries', []):
                    entries.append({
                        'rule_number': str(entry.get('RuleNumber', '')),
                        'protocol': entry.get('Protocol', ''),
                        'rule_action': entry.get('RuleAction', ''),
                        'cidr_block': entry.get('CidrBlock', ''),
                        'egress': str(entry.get('Egress', False))
                    })
                
                subnet_associations = [
                    assoc['SubnetId'] for assoc in acl_data.get('Associations', [])
                ]
                
                network_acl = NetworkACL(
                    resource_id=acl_data['NetworkAclId'],
                    resource_type='network_acl',
                    region=self.region,
                    tags=tags,
                    vpc_id=acl_data['VpcId'],
                    is_default=acl_data.get('IsDefault', False),
                    subnet_associations=subnet_associations,
                    entries=entries
                )
                network_acls.append(network_acl)
            
            return network_acls
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover Network ACLs for VPC {vpc_id}: {e}")
    
    def discover_security_groups(self, vpc_id: str) -> List[SecurityGroup]:
        """Discover Security Groups for a given VPC."""
        try:
            response = self.boto3_caller.call_api(
                'ec2', 'describe_security_groups',
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            security_groups = []
            
            for sg_data in response['SecurityGroups']:
                tags = {tag['Key']: tag['Value'] for tag in sg_data.get('Tags', [])}
                
                inbound_rules = []
                for rule in sg_data.get('IpPermissions', []):
                    for ip_range in rule.get('IpRanges', []):
                        inbound_rules.append({
                            'protocol': rule.get('IpProtocol', ''),
                            'from_port': str(rule.get('FromPort', '')),
                            'to_port': str(rule.get('ToPort', '')),
                            'cidr_block': ip_range.get('CidrIp', ''),
                            'description': ip_range.get('Description', '')
                        })
                
                outbound_rules = []
                for rule in sg_data.get('IpPermissionsEgress', []):
                    for ip_range in rule.get('IpRanges', []):
                        outbound_rules.append({
                            'protocol': rule.get('IpProtocol', ''),
                            'from_port': str(rule.get('FromPort', '')),
                            'to_port': str(rule.get('ToPort', '')),
                            'cidr_block': ip_range.get('CidrIp', ''),
                            'description': ip_range.get('Description', '')
                        })
                
                security_group = SecurityGroup(
                    resource_id=sg_data['GroupId'],
                    resource_type='security_group',
                    region=self.region,
                    tags=tags,
                    vpc_id=sg_data['VpcId'],
                    group_name=sg_data['GroupName'],
                    description=sg_data['Description'],
                    inbound_rules=inbound_rules,
                    outbound_rules=outbound_rules
                )
                security_groups.append(security_group)
            
            return security_groups
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover Security Groups for VPC {vpc_id}: {e}")
"""AWS network utilities discovery implementation."""

from typing import List, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from ..model.models import Route53HostedZone, APIGateway
from .boto3_caller import Boto3Caller
from .interfaces import NetworkUtilitiesDiscoverer


class AWSNetworkUtilitiesDiscoverer(NetworkUtilitiesDiscoverer):
    """AWS implementation of network utilities discovery."""
    
    def __init__(self, region: str = 'us-east-1', session: Optional[boto3.Session] = None):
        self.region = region
        self.boto3_caller = Boto3Caller(region, session)
    
    def discover_route53_zones(self, vpc_id: Optional[str] = None) -> List[Route53HostedZone]:
        """Discover Route53 hosted zones, optionally filtered by VPC."""
        try:
            response = self.boto3_caller.call_api('route53', 'list_hosted_zones')
            zones = []
            
            for zone_data in response['HostedZones']:
                zone_id = zone_data['Id'].split('/')[-1]
                
                try:
                    zone_details = self.boto3_caller.call_api('route53', 'get_hosted_zone', Id=zone_id)
                    zone_info = zone_details['HostedZone']
                    vpcs = zone_details.get('VPCs', [])
                    
                    vpc_associations = [vpc['VPCId'] for vpc in vpcs]
                    
                    if vpc_id and vpc_id not in vpc_associations:
                        continue
                    
                    try:
                        tags_response = self.boto3_caller.call_api(
                            'route53', 'list_tags_for_resource',
                            ResourceType='hostedzone',
                            ResourceId=zone_id
                        )
                        tags = {tag['Key']: tag['Value'] for tag in tags_response.get('ResourceTagSet', {}).get('Tags', [])}
                    except (BotoCoreError, ClientError):
                        tags = {}
                    
                    zone = Route53HostedZone(
                        resource_id=zone_id,
                        resource_type='route53_hosted_zone',
                        region=self.region,
                        tags=tags,
                        zone_name=zone_info['Name'],
                        zone_id=zone_id,
                        private_zone=zone_info.get('Config', {}).get('PrivateZone', False),
                        record_count=zone_info.get('ResourceRecordSetCount', 0),
                        vpc_associations=vpc_associations
                    )
                    zones.append(zone)
                    
                except (BotoCoreError, ClientError) as e:
                    print(f"Warning: Failed to get details for hosted zone {zone_id}: {e}")
                    continue
            
            return zones
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover Route53 hosted zones: {e}")
    
    def discover_api_gateways(self, vpc_id: Optional[str] = None) -> List[APIGateway]:
        """Discover API Gateways, optionally filtered by VPC."""
        gateways = []
        
        try:
            rest_apis = self.boto3_caller.call_api('apigateway', 'get_rest_apis')
            for api_data in rest_apis['items']:
                try:
                    tags_response = self.boto3_caller.call_api(
                        'apigateway', 'get_tags',
                        resourceArn=f"arn:aws:apigateway:{self.region}::/restapis/{api_data['id']}"
                    )
                    tags = tags_response.get('tags', {})
                except (BotoCoreError, ClientError):
                    tags = {}
                
                gateway = APIGateway(
                    resource_id=api_data['id'],
                    resource_type='api_gateway',
                    region=self.region,
                    tags=tags,
                    api_name=api_data.get('name', ''),
                    api_type='REST',
                    protocol_type='HTTP',
                    endpoint_type=api_data.get('endpointConfiguration', {}).get('types', ['EDGE'])[0],
                    vpc_links=[]
                )
                gateways.append(gateway)
                
        except (BotoCoreError, ClientError) as e:
            print(f"Warning: Failed to discover REST APIs: {e}")
        
        try:
            http_apis = self.boto3_caller.call_api('apigatewayv2', 'get_apis')
            for api_data in http_apis['Items']:
                try:
                    tags_response = self.boto3_caller.call_api(
                        'apigatewayv2', 'get_tags',
                        ResourceArn=f"arn:aws:apigateway:{self.region}::/apis/{api_data['ApiId']}"
                    )
                    tags = tags_response.get('Tags', {})
                except (BotoCoreError, ClientError):
                    tags = {}
                
                gateway = APIGateway(
                    resource_id=api_data['ApiId'],
                    resource_type='api_gateway',
                    region=self.region,
                    tags=tags,
                    api_name=api_data.get('Name', ''),
                    api_type='HTTP',
                    protocol_type=api_data.get('ProtocolType', 'HTTP'),
                    endpoint_type='REGIONAL',
                    vpc_links=[]
                )
                gateways.append(gateway)
                
        except (BotoCoreError, ClientError) as e:
            print(f"Warning: Failed to discover HTTP APIs: {e}")
        
        return gateways
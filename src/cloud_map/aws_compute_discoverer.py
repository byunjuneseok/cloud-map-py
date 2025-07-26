"""AWS compute resource discovery implementation."""

from typing import List, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .interfaces import ComputeDiscoverer
from .models import EC2Instance


class AWSComputeDiscoverer(ComputeDiscoverer):
    """AWS implementation of compute resource discovery."""
    
    def __init__(self, region: str = 'us-east-1', session: Optional[boto3.Session] = None):
        self.region = region
        self.session = session or boto3.Session()
        self.ec2_client = self.session.client('ec2', region_name=region)
    
    def discover_ec2_instances(self, subnet_id: Optional[str] = None) -> List[EC2Instance]:
        """Discover EC2 instances, optionally filtered by subnet."""
        try:
            filters = []
            if subnet_id:
                filters.append({'Name': 'subnet-id', 'Values': [subnet_id]})
            
            if filters:
                response = self.ec2_client.describe_instances(Filters=filters)
            else:
                response = self.ec2_client.describe_instances()
            
            instances = []
            
            for reservation in response['Reservations']:
                for instance_data in reservation['Instances']:
                    tags = {tag['Key']: tag['Value'] for tag in instance_data.get('Tags', [])}
                    
                    security_groups = [
                        sg['GroupId'] for sg in instance_data.get('SecurityGroups', [])
                    ]
                    
                    instance = EC2Instance(
                        resource_id=instance_data['InstanceId'],
                        resource_type='ec2_instance',
                        region=self.region,
                        tags=tags,
                        instance_type=instance_data['InstanceType'],
                        state=instance_data['State']['Name'],
                        vpc_id=instance_data.get('VpcId', ''),
                        subnet_id=instance_data.get('SubnetId', ''),
                        private_ip=instance_data.get('PrivateIpAddress', ''),
                        public_ip=instance_data.get('PublicIpAddress'),
                        security_groups=security_groups
                    )
                    instances.append(instance)
            
            return instances
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover EC2 instances: {e}")
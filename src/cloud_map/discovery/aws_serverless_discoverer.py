"""AWS serverless resource discovery implementation."""

from typing import List, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from ..model.models import LambdaFunction
from .boto3_caller import Boto3Caller
from .interfaces import ServerlessDiscoverer


class AWSServerlessDiscoverer(ServerlessDiscoverer):
    """AWS implementation of serverless resource discovery."""
    
    def __init__(self, region: str = 'us-east-1', session: Optional[boto3.Session] = None):
        self.region = region
        self.boto3_caller = Boto3Caller(region, session)
    
    def discover_lambda_functions(self, vpc_id: Optional[str] = None) -> List[LambdaFunction]:
        """Discover Lambda functions, optionally filtered by VPC."""
        try:
            response = self.boto3_caller.call_api('lambda', 'list_functions')
            functions = []
            
            for func_data in response['Functions']:
                function_name = func_data['FunctionName']
                
                try:
                    func_config = self.boto3_caller.call_api(
                        'lambda', 'get_function_configuration',
                        FunctionName=function_name
                    )
                    
                    vpc_config = func_config.get('VpcConfig', {})
                    subnet_ids = vpc_config.get('SubnetIds', [])
                    security_group_ids = vpc_config.get('SecurityGroupIds', [])
                    
                    if vpc_id and vpc_config.get('VpcId') != vpc_id:
                        continue
                    
                    tags_response = self.boto3_caller.call_api(
                        'lambda', 'list_tags',
                        Resource=func_config['FunctionArn']
                    )
                    tags = tags_response.get('Tags', {})
                    
                    lambda_func = LambdaFunction(
                        resource_id=func_config['FunctionArn'],
                        resource_type='lambda_function',
                        region=self.region,
                        tags=tags,
                        function_name=function_name,
                        runtime=func_config.get('Runtime', ''),
                        state=func_config.get('State', ''),
                        vpc_config=vpc_config if vpc_config else None,
                        subnet_ids=subnet_ids,
                        security_group_ids=security_group_ids
                    )
                    functions.append(lambda_func)
                    
                except (BotoCoreError, ClientError) as e:
                    print(f"Warning: Failed to get details for function {function_name}: {e}")
                    continue
            
            return functions
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover Lambda functions: {e}")
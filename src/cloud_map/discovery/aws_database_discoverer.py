"""AWS database resource discovery implementation."""

from typing import List, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from .interfaces import DatabaseDiscoverer
from ..model.models import RDSInstance, ElastiCacheCluster, ElastiCacheReplicationGroup, MSKCluster, RDSNode, ElastiCacheNode, MSKBrokerNode
from .boto3_caller import Boto3Caller


class AWSDatabaseDiscoverer(DatabaseDiscoverer):
    """AWS implementation of database resource discovery."""
    
    def __init__(self, region: str = 'us-east-1', session: Optional[boto3.Session] = None):
        self.region = region
        self.boto3_caller = Boto3Caller(region, session)
    
    def discover_rds_instances(self, vpc_id: Optional[str] = None) -> List[RDSInstance]:
        """Discover RDS database instances, optionally filtered by VPC."""
        try:
            response = self.boto3_caller.call_api('rds', 'describe_db_instances')
            instances = []
            
            for db_instance_data in response['DBInstances']:
                db_subnet_group = db_instance_data.get('DBSubnetGroup')
                instance_vpc_id = db_subnet_group.get('VpcId') if db_subnet_group else None
                
                # Filter by VPC if specified
                if vpc_id and instance_vpc_id != vpc_id:
                    continue
                
                tags_response = self.boto3_caller.call_api(
                    'rds', 
                    'list_tags_for_resource',
                    ResourceName=db_instance_data['DBInstanceArn']
                )
                tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
                
                endpoint_data = db_instance_data.get('Endpoint', {})
                
                instance = RDSInstance(
                    resource_id=db_instance_data['DBInstanceIdentifier'],
                    resource_type='rds_instance',
                    region=self.region,
                    tags=tags,
                    db_instance_identifier=db_instance_data['DBInstanceIdentifier'],
                    db_instance_class=db_instance_data['DBInstanceClass'],
                    engine=db_instance_data['Engine'],
                    engine_version=db_instance_data['EngineVersion'],
                    db_name=db_instance_data.get('DBName'),
                    endpoint=endpoint_data.get('Address'),
                    port=endpoint_data.get('Port', 0),
                    vpc_id=instance_vpc_id,
                    subnet_group_name=db_subnet_group.get('DBSubnetGroupName') if db_subnet_group else None,
                    availability_zone=db_instance_data.get('AvailabilityZone', ''),
                    multi_az=db_instance_data.get('MultiAZ', False),
                    publicly_accessible=db_instance_data.get('PubliclyAccessible', False),
                    storage_type=db_instance_data.get('StorageType', ''),
                    allocated_storage=db_instance_data.get('AllocatedStorage', 0),
                    storage_encrypted=db_instance_data.get('StorageEncrypted', False),
                    db_instance_status=db_instance_data.get('DBInstanceStatus', ''),
                    read_replica_source=db_instance_data.get('ReadReplicaSourceDBInstanceIdentifier'),
                    read_replica_db_instance_identifiers=db_instance_data.get('ReadReplicaDBInstanceIdentifiers', [])
                )
                instances.append(instance)
            
            return instances
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover RDS instances: {e}")
    
    def discover_elasticache_clusters(self, vpc_id: Optional[str] = None) -> List[ElastiCacheCluster]:
        """Discover ElastiCache clusters, optionally filtered by VPC."""
        try:
            response = self.boto3_caller.call_api('elasticache', 'describe_cache_clusters', ShowCacheNodeInfo=True)
            clusters = []
            
            for cluster_data in response['CacheClusters']:
                cache_subnet_group = cluster_data.get('CacheSubnetGroupName')
                cluster_vpc_id = None
                
                # Get VPC ID from subnet group if available
                if cache_subnet_group:
                    try:
                        subnet_response = self.boto3_caller.call_api(
                            'elasticache', 
                            'describe_cache_subnet_groups',
                            CacheSubnetGroupName=cache_subnet_group
                        )
                        if subnet_response['CacheSubnetGroups']:
                            cluster_vpc_id = subnet_response['CacheSubnetGroups'][0].get('VpcId')
                    except (BotoCoreError, ClientError):
                        pass  # Continue without VPC ID if subnet group lookup fails
                
                # Filter by VPC if specified
                if vpc_id and cluster_vpc_id != vpc_id:
                    continue
                
                # Get tags
                try:
                    tags_response = self.boto3_caller.call_api(
                        'elasticache',
                        'list_tags_for_resource',
                        ResourceName=cluster_data['ARN']
                    )
                    tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
                except (BotoCoreError, ClientError):
                    tags = {}
                
                security_group_ids = [
                    sg['SecurityGroupId'] for sg in cluster_data.get('SecurityGroups', [])
                ]
                
                cache_nodes = []
                for node in cluster_data.get('CacheNodes', []):
                    cache_nodes.append({
                        'CacheNodeId': node.get('CacheNodeId', ''),
                        'CacheNodeStatus': node.get('CacheNodeStatus', ''),
                        'AvailabilityZone': node.get('CustomerAvailabilityZone', ''),
                        'Endpoint': node.get('Endpoint', {}).get('Address', '') if node.get('Endpoint') else ''
                    })
                
                cluster = ElastiCacheCluster(
                    resource_id=cluster_data['CacheClusterId'],
                    resource_type='elasticache_cluster',
                    region=self.region,
                    tags=tags,
                    cache_cluster_id=cluster_data['CacheClusterId'],
                    cache_node_type=cluster_data.get('CacheNodeType', ''),
                    engine=cluster_data.get('Engine', ''),
                    engine_version=cluster_data.get('EngineVersion', ''),
                    cache_cluster_status=cluster_data.get('CacheClusterStatus', ''),
                    num_cache_nodes=cluster_data.get('NumCacheNodes', 0),
                    preferred_availability_zone=cluster_data.get('PreferredAvailabilityZone'),
                    cache_subnet_group_name=cache_subnet_group,
                    vpc_id=cluster_vpc_id,
                    security_group_ids=security_group_ids,
                    port=cluster_data.get('RedisConfiguration', {}).get('Port', 0) if cluster_data.get('RedisConfiguration') else 0,
                    parameter_group_name=cluster_data.get('CacheParameterGroup', {}).get('CacheParameterGroupName', '') if cluster_data.get('CacheParameterGroup') else '',
                    cache_nodes=cache_nodes,
                    replication_group_id=cluster_data.get('ReplicationGroupId')
                )
                clusters.append(cluster)
            
            return clusters
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover ElastiCache clusters: {e}")
    
    def discover_elasticache_replication_groups(self, vpc_id: Optional[str] = None) -> List[ElastiCacheReplicationGroup]:
        """Discover ElastiCache replication groups, optionally filtered by VPC."""
        try:
            response = self.boto3_caller.call_api('elasticache', 'describe_replication_groups')
            replication_groups = []
            
            for rg_data in response['ReplicationGroups']:
                # Get VPC ID from first member cluster's subnet group
                rg_vpc_id = None
                member_clusters = rg_data.get('MemberClusters', [])
                
                if member_clusters:
                    try:
                        cluster_response = self.boto3_caller.call_api(
                            'elasticache',
                            'describe_cache_clusters',
                            CacheClusterId=member_clusters[0]
                        )
                        if cluster_response['CacheClusters']:
                            cache_subnet_group = cluster_response['CacheClusters'][0].get('CacheSubnetGroupName')
                            if cache_subnet_group:
                                subnet_response = self.boto3_caller.call_api(
                                    'elasticache',
                                    'describe_cache_subnet_groups',
                                    CacheSubnetGroupName=cache_subnet_group
                                )
                                if subnet_response['CacheSubnetGroups']:
                                    rg_vpc_id = subnet_response['CacheSubnetGroups'][0].get('VpcId')
                    except (BotoCoreError, ClientError):
                        pass
                
                # Filter by VPC if specified
                if vpc_id and rg_vpc_id != vpc_id:
                    continue
                
                # Get tags
                try:
                    tags_response = self.boto3_caller.call_api(
                        'elasticache',
                        'list_tags_for_resource',
                        ResourceName=rg_data['ARN']
                    )
                    tags = {tag['Key']: tag['Value'] for tag in tags_response.get('TagList', [])}
                except (BotoCoreError, ClientError):
                    tags = {}
                
                security_group_ids = [
                    sg['SecurityGroupId'] for sg in rg_data.get('GlobalReplicationGroupInfo', {}).get('GlobalReplicationGroupMemberRole', {}).get('SecurityGroups', [])
                ] if rg_data.get('GlobalReplicationGroupInfo') else []
                
                node_groups = []
                for ng in rg_data.get('NodeGroups', []):
                    node_groups.append({
                        'NodeGroupId': ng.get('NodeGroupId', ''),
                        'Status': ng.get('Status', ''),
                        'PrimaryEndpoint': ng.get('PrimaryEndpoint', {}).get('Address', '') if ng.get('PrimaryEndpoint') else '',
                        'ReaderEndpoint': ng.get('ReaderEndpoint', {}).get('Address', '') if ng.get('ReaderEndpoint') else ''
                    })
                
                cache_subnet_group_name = None
                if member_clusters:
                    try:
                        cluster_response = self.boto3_caller.call_api(
                            'elasticache',
                            'describe_cache_clusters',
                            CacheClusterId=member_clusters[0]
                        )
                        if cluster_response['CacheClusters']:
                            cache_subnet_group_name = cluster_response['CacheClusters'][0].get('CacheSubnetGroupName')
                    except (BotoCoreError, ClientError):
                        pass
                
                replication_group = ElastiCacheReplicationGroup(
                    resource_id=rg_data['ReplicationGroupId'],
                    resource_type='elasticache_replication_group',
                    region=self.region,
                    tags=tags,
                    replication_group_id=rg_data['ReplicationGroupId'],
                    description=rg_data.get('Description', ''),
                    status=rg_data.get('Status', ''),
                    primary_cluster_id=rg_data.get('PrimaryClusterId'),
                    member_clusters=member_clusters,
                    node_groups=node_groups,
                    cache_node_type=rg_data.get('CacheNodeType', ''),
                    engine=rg_data.get('Engine', ''),
                    engine_version=rg_data.get('EngineVersion', ''),
                    cache_subnet_group_name=cache_subnet_group_name,
                    vpc_id=rg_vpc_id,
                    security_group_ids=security_group_ids,
                    port=rg_data.get('ConfigurationEndpoint', {}).get('Port', 0) if rg_data.get('ConfigurationEndpoint') else 0,
                    multi_az=rg_data.get('MultiAZ', ''),
                    automatic_failover=rg_data.get('AutomaticFailover', '')
                )
                replication_groups.append(replication_group)
            
            return replication_groups
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover ElastiCache replication groups: {e}")
    
    def discover_msk_clusters(self, vpc_id: Optional[str] = None) -> List[MSKCluster]:
        """Discover MSK Kafka clusters, optionally filtered by VPC."""
        try:
            response = self.boto3_caller.call_api('kafka', 'list_clusters')
            clusters = []
            
            for cluster_info in response['ClusterInfoList']:
                cluster_vpc_id = cluster_info.get('BrokerNodeGroupInfo', {}).get('ClientSubnets', [])
                
                # Get VPC ID from first subnet
                cluster_vpc_id_resolved = None
                if cluster_vpc_id:
                    try:
                        subnet_response = self.boto3_caller.call_api(
                            'ec2',
                            'describe_subnets',
                            SubnetIds=[cluster_vpc_id[0]]
                        )
                        if subnet_response['Subnets']:
                            cluster_vpc_id_resolved = subnet_response['Subnets'][0].get('VpcId')
                    except (BotoCoreError, ClientError):
                        pass
                
                # Filter by VPC if specified
                if vpc_id and cluster_vpc_id_resolved != vpc_id:
                    continue
                
                # Get detailed cluster information
                cluster_arn = cluster_info['ClusterArn']
                try:
                    cluster_detail = self.boto3_caller.call_api(
                        'kafka',
                        'describe_cluster',
                        ClusterArn=cluster_arn
                    )
                    cluster_data = cluster_detail['ClusterInfo']
                except (BotoCoreError, ClientError):
                    cluster_data = cluster_info
                
                # Get tags
                try:
                    tags_response = self.boto3_caller.call_api(
                        'kafka',
                        'list_tags_for_resource',
                        ResourceArn=cluster_arn
                    )
                    tags = tags_response.get('Tags', {})
                except (BotoCoreError, ClientError):
                    tags = {}
                
                # Get broker node information
                broker_nodes = []
                try:
                    nodes_response = self.boto3_caller.call_api(
                        'kafka',
                        'list_nodes',
                        ClusterArn=cluster_arn
                    )
                    
                    for node_info in nodes_response.get('NodeInfoList', []):
                        broker_node = MSKBrokerNode(
                            resource_id=f"{cluster_data['ClusterName']}-broker-{node_info.get('BrokerNodeInfo', {}).get('BrokerId', '')}",
                            resource_type='msk_broker_node',
                            region=self.region,
                            tags=tags,
                            broker_id=str(node_info.get('BrokerNodeInfo', {}).get('BrokerId', '')),
                            cluster_arn=cluster_arn,
                            instance_type=cluster_data.get('BrokerNodeGroupInfo', {}).get('InstanceType', ''),
                            availability_zone=node_info.get('BrokerNodeInfo', {}).get('AvailabilityZone', ''),
                            subnet_id=node_info.get('BrokerNodeInfo', {}).get('ClientSubnet', ''),
                            client_subnet=node_info.get('BrokerNodeInfo', {}).get('ClientSubnet', ''),
                            endpoint=node_info.get('BrokerNodeInfo', {}).get('Endpoints', [{}])[0] if node_info.get('BrokerNodeInfo', {}).get('Endpoints') else None,
                            client_vpc_ip_address=node_info.get('BrokerNodeInfo', {}).get('ClientVpcIpAddress', ''),
                            status=cluster_data.get('State', '')
                        )
                        broker_nodes.append(broker_node)
                        
                except (BotoCoreError, ClientError):
                    pass  # Continue without detailed node info
                
                broker_node_group_info = cluster_data.get('BrokerNodeGroupInfo', {})
                
                cluster = MSKCluster(
                    resource_id=cluster_data['ClusterName'],
                    resource_type='msk_cluster',
                    region=self.region,
                    tags=tags,
                    cluster_name=cluster_data['ClusterName'],
                    cluster_arn=cluster_arn,
                    kafka_version=cluster_data.get('CurrentBrokerSoftwareInfo', {}).get('KafkaVersion', ''),
                    number_of_broker_nodes=cluster_data.get('NumberOfBrokerNodes', 0),
                    instance_type=broker_node_group_info.get('InstanceType', ''),
                    state=cluster_data.get('State', ''),
                    creation_time=cluster_data.get('CreationTime', ''),
                    current_version=cluster_data.get('CurrentVersion', ''),
                    broker_node_group_info=broker_node_group_info,
                    subnet_ids=broker_node_group_info.get('ClientSubnets', []),
                    security_group_ids=broker_node_group_info.get('SecurityGroups', []),
                    vpc_id=cluster_vpc_id_resolved,
                    encryption_info=cluster_data.get('EncryptionInfo', {}),
                    client_authentication=cluster_data.get('ClientAuthentication', {}),
                    logging_info=cluster_data.get('LoggingInfo', {}),
                    broker_nodes=broker_nodes,
                    zookeeper_connect_string=cluster_data.get('ZookeeperConnectString'),
                    bootstrap_broker_string=cluster_data.get('BootstrapBrokerString')
                )
                clusters.append(cluster)
            
            return clusters
            
        except (BotoCoreError, ClientError) as e:
            raise RuntimeError(f"Failed to discover MSK clusters: {e}")
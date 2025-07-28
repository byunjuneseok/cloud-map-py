"""Diagram generation for cloud infrastructure visualization."""

from typing import List, TextIO
from ..executor.organizer import AccountTopology, NetworkTopology
from ..model.models import Subnet, EC2Instance
from .interfaces import DiagramGenerator


class TextDiagramGenerator(DiagramGenerator):
    """Generates text-based diagrams of cloud infrastructure."""
    
    def __init__(self, output_manager=None, session_dir=None, indent_size: int = 2):
        self.output_manager = output_manager
        self.session_dir = session_dir
        self.indent_size = indent_size
    
    def _indent(self, level: int) -> str:
        """Generate indentation string for given level."""
        return " " * (level * self.indent_size)
    
    def generate_subnet_diagram(self, topology: NetworkTopology, output: TextIO) -> None:
        """Generate diagram at subnet level showing resources grouped by AZ."""
        # Reset tracking variables for each diagram
        self._displayed_rds_instances = set()
        self._displayed_cache_instances = set()
        
        output.write(f"VPC: {topology.vpc.name or topology.vpc.resource_id} ({topology.vpc.cidr_block})\n")
        
        # Display routing table information
        if topology.route_tables:
            output.write(f"{self._indent(1)}Routing Tables:\n")
            for rt in topology.route_tables:
                rt_name = rt.name or rt.resource_id
                output.write(f"{self._indent(2)}{rt_name}:\n")
                output.write(f"{self._indent(3)}+-{'-'*25}+-{'-'*25}+\n")
                output.write(f"{self._indent(3)}| {'Destination':<25} | {'Target':<25} |\n")
                output.write(f"{self._indent(3)}+-{'-'*25}+-{'-'*25}+\n")
                for route in rt.routes[:5]:  # Show first 5 routes
                    dest = route.get('destination', 'N/A')[:25]
                    gateway = route.get('gateway_id', 'local')[:25]
                    output.write(f"{self._indent(3)}| {dest:<25} | {gateway:<25} |\n")
                output.write(f"{self._indent(3)}+-{'-'*25}+-{'-'*25}+\n")
            output.write("\n")
        
        # Group subnets by Availability Zone
        az_groups = {}
        for subnet in topology.subnets:
            az = subnet.availability_zone
            if az not in az_groups:
                az_groups[az] = {'public': [], 'private': []}
            
            if subnet.map_public_ip_on_launch:
                az_groups[az]['public'].append(subnet)
            else:
                az_groups[az]['private'].append(subnet)
        
        # Display by AZ
        for az, subnet_groups in az_groups.items():
            output.write(f"{self._indent(1)}Availability Zone: {az}\n")
            
            # Public subnets in this AZ
            if subnet_groups['public']:
                output.write(f"{self._indent(2)}Public Subnets:\n")
                for subnet in subnet_groups['public']:
                    output.write(f"{self._indent(3)}{subnet.name or subnet.resource_id} ({subnet.cidr_block})\n")
                    
                    # NAT Gateways in this subnet
                    nat_gateways = [nat for nat in topology.nat_gateways if nat.subnet_id == subnet.resource_id]
                    if nat_gateways:
                        for nat in nat_gateways:
                            output.write(f"{self._indent(4)}├─ NAT Gateway: {nat.name or nat.resource_id}\n")
                            output.write(f"{self._indent(5)}Type: {nat.nat_gateway_type}, State: {nat.state}\n")
                            output.write(f"{self._indent(5)}→ Routes outbound traffic to Internet Gateway\n")
                    
                    # EC2 instances
                    instances = topology.get_instances_by_subnet(subnet.resource_id)
                    for instance in instances:
                        output.write(f"{self._indent(4)}├─ EC2: {instance.name or instance.resource_id}\n")
                        output.write(f"{self._indent(5)}Type: {instance.instance_type}, State: {instance.state}\n")
                        output.write(f"{self._indent(5)}Private IP: {instance.private_ip}\n")
                        if instance.public_ip:
                            output.write(f"{self._indent(5)}Public IP: {instance.public_ip}\n")
                    
                    # RDS instances in this subnet
                    rds_instances = topology.get_rds_instances_by_subnet(subnet.resource_id)
                    for rds in rds_instances:
                        if rds.resource_id not in self._displayed_rds_instances:
                            self._displayed_rds_instances.add(rds.resource_id)
                            output.write(f"{self._indent(4)}├─ RDS: {rds.name or rds.db_instance_identifier}\n")
                            output.write(f"{self._indent(5)}Engine: {rds.engine} {rds.engine_version}\n")
                            output.write(f"{self._indent(5)}Class: {rds.db_instance_class}, Status: {rds.db_instance_status}\n")
                            if rds.endpoint:
                                output.write(f"{self._indent(5)}Endpoint: {rds.endpoint}:{rds.port}\n")
                            output.write(f"{self._indent(5)}Multi-AZ: {rds.multi_az}, Encrypted: {rds.storage_encrypted}\n")
                            if rds.read_replica_db_instance_identifiers:
                                output.write(f"{self._indent(5)}Read Replicas: {len(rds.read_replica_db_instance_identifiers)}\n")
                            if rds.read_replica_source:
                                output.write(f"{self._indent(5)}Read Replica of: {rds.read_replica_source}\n")
                    
                    # ElastiCache clusters in this subnet
                    cache_clusters = topology.get_elasticache_clusters_by_subnet(subnet.resource_id)
                    for cache in cache_clusters:
                        if (not cache.replication_group_id and 
                            cache.resource_id not in self._displayed_cache_instances):
                            self._displayed_cache_instances.add(cache.resource_id)
                            output.write(f"{self._indent(4)}├─ ElastiCache: {cache.name or cache.cache_cluster_id}\n")
                            output.write(f"{self._indent(5)}Engine: {cache.engine} {cache.engine_version}\n")
                            output.write(f"{self._indent(5)}Type: {cache.cache_node_type}, Status: {cache.cache_cluster_status}\n")
                            output.write(f"{self._indent(5)}Nodes: {cache.num_cache_nodes}\n")
                    
                    # ElastiCache replication groups (show once per VPC)
                    replication_groups = topology.get_elasticache_replication_groups_by_subnet(subnet.resource_id)
                    for rg in replication_groups:
                        if rg.resource_id not in self._displayed_cache_instances:
                            self._displayed_cache_instances.add(rg.resource_id)
                            output.write(f"{self._indent(4)}├─ ElastiCache Cluster: {rg.name or rg.replication_group_id}\n")
                            output.write(f"{self._indent(5)}Engine: {rg.engine} {rg.engine_version}\n")
                            output.write(f"{self._indent(5)}Type: {rg.cache_node_type}, Status: {rg.status}\n")
                            output.write(f"{self._indent(5)}Multi-AZ: {rg.multi_az}, Auto Failover: {rg.automatic_failover}\n")
                            if rg.member_clusters:
                                output.write(f"{self._indent(5)}Member Clusters: {len(rg.member_clusters)}\n")
                    
                    # MSK Kafka broker nodes in this public subnet
                    msk_broker_nodes = topology.get_msk_broker_nodes_by_subnet(subnet.resource_id)
                    for broker in msk_broker_nodes:
                        output.write(f"{self._indent(4)}├─ MSK Broker: {broker.name or broker.broker_id}\n")
                        output.write(f"{self._indent(5)}Cluster: {broker.cluster_arn.split('/')[-1]}\n")
                        output.write(f"{self._indent(5)}Instance Type: {broker.instance_type}\n")
                        output.write(f"{self._indent(5)}Status: {broker.status}\n")
                        if broker.client_vpc_ip_address:
                            output.write(f"{self._indent(5)}VPC IP: {broker.client_vpc_ip_address}\n")
            
            # Private subnets in this AZ
            if subnet_groups['private']:
                output.write(f"{self._indent(2)}Private Subnets:\n")
                for subnet in subnet_groups['private']:
                    output.write(f"{self._indent(3)}{subnet.name or subnet.resource_id} ({subnet.cidr_block})\n")
                    
                    # EC2 instances
                    instances = topology.get_instances_by_subnet(subnet.resource_id)
                    for instance in instances:
                        output.write(f"{self._indent(4)}├─ EC2: {instance.name or instance.resource_id}\n")
                        output.write(f"{self._indent(5)}Type: {instance.instance_type}, State: {instance.state}\n")
                        output.write(f"{self._indent(5)}Private IP: {instance.private_ip}\n")
                        if topology.nat_gateways:
                            output.write(f"{self._indent(5)}→ Routes outbound traffic via NAT Gateway\n")
                    
                    # RDS instances in this subnet
                    rds_instances = topology.get_rds_instances_by_subnet(subnet.resource_id)
                    for rds in rds_instances:
                        if rds.resource_id not in self._displayed_rds_instances:
                            self._displayed_rds_instances.add(rds.resource_id)
                            output.write(f"{self._indent(4)}├─ RDS: {rds.name or rds.db_instance_identifier}\n")
                            output.write(f"{self._indent(5)}Engine: {rds.engine} {rds.engine_version}\n")
                            output.write(f"{self._indent(5)}Class: {rds.db_instance_class}, Status: {rds.db_instance_status}\n")
                            if rds.endpoint:
                                output.write(f"{self._indent(5)}Endpoint: {rds.endpoint}:{rds.port}\n")
                            output.write(f"{self._indent(5)}Multi-AZ: {rds.multi_az}, Encrypted: {rds.storage_encrypted}\n")
                            if rds.read_replica_db_instance_identifiers:
                                output.write(f"{self._indent(5)}Read Replicas: {len(rds.read_replica_db_instance_identifiers)}\n")
                            if rds.read_replica_source:
                                output.write(f"{self._indent(5)}Read Replica of: {rds.read_replica_source}\n")
                    
                    # ElastiCache clusters in this subnet
                    cache_clusters = topology.get_elasticache_clusters_by_subnet(subnet.resource_id)
                    for cache in cache_clusters:
                        if (not cache.replication_group_id and 
                            cache.resource_id not in self._displayed_cache_instances):
                            self._displayed_cache_instances.add(cache.resource_id)
                            output.write(f"{self._indent(4)}├─ ElastiCache: {cache.name or cache.cache_cluster_id}\n")
                            output.write(f"{self._indent(5)}Engine: {cache.engine} {cache.engine_version}\n")
                            output.write(f"{self._indent(5)}Type: {cache.cache_node_type}, Status: {cache.cache_cluster_status}\n")
                            output.write(f"{self._indent(5)}Nodes: {cache.num_cache_nodes}\n")
                    
                    # ElastiCache replication groups (show once per VPC)
                    replication_groups = topology.get_elasticache_replication_groups_by_subnet(subnet.resource_id)
                    for rg in replication_groups:
                        if rg.resource_id not in self._displayed_cache_instances:
                            self._displayed_cache_instances.add(rg.resource_id)
                            output.write(f"{self._indent(4)}├─ ElastiCache Cluster: {rg.name or rg.replication_group_id}\n")
                            output.write(f"{self._indent(5)}Engine: {rg.engine} {rg.engine_version}\n")
                            output.write(f"{self._indent(5)}Type: {rg.cache_node_type}, Status: {rg.status}\n")
                            output.write(f"{self._indent(5)}Multi-AZ: {rg.multi_az}, Auto Failover: {rg.automatic_failover}\n")
                            if rg.member_clusters:
                                output.write(f"{self._indent(5)}Member Clusters: {len(rg.member_clusters)}\n")
                    
                    # MSK Kafka broker nodes in this private subnet  
                    msk_broker_nodes = topology.get_msk_broker_nodes_by_subnet(subnet.resource_id)
                    for broker in msk_broker_nodes:
                        output.write(f"{self._indent(4)}├─ MSK Broker: {broker.name or broker.broker_id}\n")
                        output.write(f"{self._indent(5)}Cluster: {broker.cluster_arn.split('/')[-1]}\n")
                        output.write(f"{self._indent(5)}Instance Type: {broker.instance_type}\n")
                        output.write(f"{self._indent(5)}Status: {broker.status}\n")
                        if broker.client_vpc_ip_address:
                            output.write(f"{self._indent(5)}VPC IP: {broker.client_vpc_ip_address}\n")
            
            output.write("\n")
    
    def generate_vpc_diagram(self, topology: NetworkTopology, output: TextIO) -> None:
        """Generate diagram at VPC level with network flow visualization."""
        output.write(f"VPC: {topology.vpc.name or topology.vpc.resource_id}\n")
        output.write(f"{self._indent(1)}CIDR: {topology.vpc.cidr_block}\n")
        output.write(f"{self._indent(1)}State: {topology.vpc.state}\n")
        output.write(f"{self._indent(1)}Default: {topology.vpc.is_default}\n")
        
        # Network Flow Overview
        output.write(f"\n{self._indent(1)}Network Flow:\n")
        if topology.internet_gateways and topology.nat_gateways:
            output.write(f"{self._indent(2)}Internet ←→ Internet Gateway ←→ NAT Gateway ←→ Private Subnets\n")
        elif topology.internet_gateways:
            output.write(f"{self._indent(2)}Internet ←→ Internet Gateway ←→ Public Subnets\n")
        
        if topology.api_gateways:
            output.write(f"{self._indent(2)}API Gateway ←→ Internet Gateway ←→ Internet\n")
        
        if topology.route53_zones:
            for zone in topology.route53_zones:
                zone_type = "Private" if zone.private_zone else "Public"
                output.write(f"{self._indent(2)}Route53 ({zone_type}) ←→ DNS queries\n")
        
        if topology.internet_gateways:
            output.write(f"\n{self._indent(1)}Internet Gateways:\n")
            for igw in topology.internet_gateways:
                output.write(f"{self._indent(2)}{igw.resource_id} ({igw.state})\n")
        
        if topology.nat_gateways:
            output.write(f"{self._indent(1)}NAT Gateways:\n")
            for nat in topology.nat_gateways:
                output.write(f"{self._indent(2)}{nat.name or nat.resource_id} ({nat.state})\n")
                output.write(f"{self._indent(3)}→ Routes outbound traffic to Internet Gateway\n")
        
        if topology.route53_zones:
            output.write(f"{self._indent(1)}Route53 Zones:\n")
            for zone in topology.route53_zones:
                zone_type = "Private" if zone.private_zone else "Public"
                output.write(f"{self._indent(2)}{zone.zone_name} ({zone_type})\n")
        
        if topology.api_gateways:
            output.write(f"{self._indent(1)}API Gateways:\n")
            for api in topology.api_gateways:
                output.write(f"{self._indent(2)}{api.api_name} ({api.api_type})\n")
                output.write(f"{self._indent(3)}→ Routes API calls via Internet Gateway\n")
        
        # Group subnets by AZ for summary
        az_groups = {}
        for subnet in topology.subnets:
            az = subnet.availability_zone
            if az not in az_groups:
                az_groups[az] = {'public': 0, 'private': 0}
            
            if subnet.map_public_ip_on_launch:
                az_groups[az]['public'] += 1
            else:
                az_groups[az]['private'] += 1
        
        output.write(f"{self._indent(1)}Subnets by Availability Zone:\n")
        for az, counts in az_groups.items():
            output.write(f"{self._indent(2)}{az}: {counts['public']} public, {counts['private']} private\n")
        
        if topology.security_groups:
            output.write(f"{self._indent(1)}Security Groups: {len(topology.security_groups)}\n")
        
        if topology.network_acls:
            output.write(f"{self._indent(1)}Network ACLs: {len(topology.network_acls)}\n")
        
        total_instances = len(topology.ec2_instances)
        if total_instances:
            output.write(f"{self._indent(1)}Total EC2 Instances: {total_instances}\n")
        
        # Database resources summary
        if topology.rds_instances:
            read_replicas = sum(len(rds.read_replica_db_instance_identifiers) for rds in topology.rds_instances)
            primary_dbs = len([rds for rds in topology.rds_instances if not rds.read_replica_source])
            output.write(f"{self._indent(1)}RDS Instances: {len(topology.rds_instances)} ({primary_dbs} primary, {read_replicas} read replicas)\n")
        
        if topology.elasticache_clusters or topology.elasticache_replication_groups:
            cache_count = len(topology.elasticache_clusters) + len(topology.elasticache_replication_groups)
            output.write(f"{self._indent(1)}ElastiCache Clusters: {cache_count}\n")
        
        output.write("\n")
    
    def generate_account_diagram(self, account_topology: AccountTopology, output: TextIO) -> None:
        """Generate diagram at account level."""
        output.write(f"AWS Account - Region: {account_topology.region}\n")
        output.write(f"Total VPCs: {len(account_topology.vpcs)}\n")
        output.write(f"Total Instances: {len(account_topology.get_all_instances())}\n")
        output.write(f"Total Subnets: {len(account_topology.get_all_subnets())}\n")
        output.write("\n")
        
        for vpc_topology in account_topology.vpcs:
            self.generate_vpc_diagram(vpc_topology, output)
    
    def generate_full_diagram(self, account_topology: AccountTopology, output: TextIO) -> None:
        """Generate complete detailed diagram."""
        content_lines = []
        content_lines.append("=" * 60)
        content_lines.append("AWS CLOUD INFRASTRUCTURE MAP")
        content_lines.append("=" * 60)
        content_lines.append("")
        
        # Generate account diagram content
        from io import StringIO
        account_output = StringIO()
        self.generate_account_diagram(account_topology, account_output)
        content_lines.append(account_output.getvalue())
        
        content_lines.append("DETAILED VPC BREAKDOWN:")
        content_lines.append("-" * 30)
        content_lines.append("")
        
        for vpc_topology in account_topology.vpcs:
            vpc_output = StringIO()
            self.generate_subnet_diagram(vpc_topology, vpc_output)
            content_lines.append(vpc_output.getvalue())
            content_lines.append("-" * 30)
        
        content = "\n".join(content_lines)
        output.write(content)
        
        # Save to file if output manager is available
        if self.output_manager and self.session_dir:
            self.output_manager.save_terminal_output(content, self.session_dir, account_topology.region)
    

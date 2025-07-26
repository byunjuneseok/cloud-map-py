"""Diagram generation for cloud infrastructure visualization."""

from typing import List, TextIO
from .organizer import AccountTopology, NetworkTopology
from .models import Subnet, EC2Instance


class TextDiagramGenerator:
    """Generates text-based diagrams of cloud infrastructure."""
    
    def __init__(self, indent_size: int = 2):
        self.indent_size = indent_size
    
    def _indent(self, level: int) -> str:
        """Generate indentation string for given level."""
        return " " * (level * self.indent_size)
    
    def generate_subnet_diagram(self, topology: NetworkTopology, output: TextIO) -> None:
        """Generate diagram at subnet level showing resources."""
        output.write(f"VPC: {topology.vpc.name or topology.vpc.resource_id} ({topology.vpc.cidr_block})\n")
        
        for subnet in topology.subnets:
            subnet_type = "Public" if subnet.map_public_ip_on_launch else "Private"
            output.write(f"{self._indent(1)}{subnet_type} Subnet: {subnet.name or subnet.resource_id}\n")
            output.write(f"{self._indent(2)}CIDR: {subnet.cidr_block}\n")
            output.write(f"{self._indent(2)}AZ: {subnet.availability_zone}\n")
            
            instances = topology.get_instances_by_subnet(subnet.resource_id)
            if instances:
                output.write(f"{self._indent(2)}EC2 Instances:\n")
                for instance in instances:
                    output.write(f"{self._indent(3)}{instance.name or instance.resource_id}\n")
                    output.write(f"{self._indent(4)}Type: {instance.instance_type}\n")
                    output.write(f"{self._indent(4)}State: {instance.state}\n")
                    output.write(f"{self._indent(4)}Private IP: {instance.private_ip}\n")
                    if instance.public_ip:
                        output.write(f"{self._indent(4)}Public IP: {instance.public_ip}\n")
            output.write("\n")
    
    def generate_vpc_diagram(self, topology: NetworkTopology, output: TextIO) -> None:
        """Generate diagram at VPC level."""
        output.write(f"VPC: {topology.vpc.name or topology.vpc.resource_id}\n")
        output.write(f"{self._indent(1)}CIDR: {topology.vpc.cidr_block}\n")
        output.write(f"{self._indent(1)}State: {topology.vpc.state}\n")
        output.write(f"{self._indent(1)}Default: {topology.vpc.is_default}\n")
        
        if topology.internet_gateways:
            output.write(f"{self._indent(1)}Internet Gateways:\n")
            for igw in topology.internet_gateways:
                output.write(f"{self._indent(2)}{igw.resource_id} ({igw.state})\n")
        
        public_subnets = topology.get_public_subnets()
        private_subnets = topology.get_private_subnets()
        
        if public_subnets:
            output.write(f"{self._indent(1)}Public Subnets: {len(public_subnets)}\n")
        if private_subnets:
            output.write(f"{self._indent(1)}Private Subnets: {len(private_subnets)}\n")
        
        total_instances = len(topology.ec2_instances)
        if total_instances:
            output.write(f"{self._indent(1)}Total EC2 Instances: {total_instances}\n")
        
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
        output.write("=" * 60 + "\n")
        output.write("AWS CLOUD INFRASTRUCTURE MAP\n")
        output.write("=" * 60 + "\n\n")
        
        self.generate_account_diagram(account_topology, output)
        
        output.write("DETAILED VPC BREAKDOWN:\n")
        output.write("-" * 30 + "\n\n")
        
        for vpc_topology in account_topology.vpcs:
            self.generate_subnet_diagram(vpc_topology, output)
            output.write("-" * 30 + "\n")
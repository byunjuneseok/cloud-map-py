"""PlantUML diagram generation for cloud infrastructure visualization."""

from typing import TextIO, Optional
from pathlib import Path
from ..executor.organizer import AccountTopology, NetworkTopology
from .interfaces import DiagramGenerator


class PlantUMLDiagramGenerator(DiagramGenerator):
    """Generates PlantUML diagrams of cloud infrastructure."""
    
    def __init__(self, output_manager=None, session_dir: Optional[Path] = None):
        self.output_manager = output_manager
        self.session_dir = session_dir
    
    def generate_full_diagram(self, account_topology: AccountTopology, output: TextIO) -> None:
        """Generate a full PlantUML diagram of the account topology."""
        content = self._generate_plantuml_content(account_topology)
        output.write(content)
        
        # Save to files if output manager is available
        if self.output_manager and self.session_dir:
            self.output_manager.save_plantuml_output(content, self.session_dir, account_topology.region)
    
    def _generate_plantuml_content(self, account_topology: AccountTopology) -> str:
        """Generate PlantUML content as string."""
        lines = []
        lines.append("@startuml")
        lines.append("!define AWSPuml https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/v20.0/dist")
        lines.append("!include AWSPuml/AWSCommon.puml")
        lines.append("!include AWSPuml/AWSSimplified.puml")
        lines.append("!include AWSPuml/Compute/EC2.puml")
        lines.append("!include AWSPuml/Compute/EC2Instance.puml")
        lines.append("!include AWSPuml/Compute/Lambda.puml")
        lines.append("!include AWSPuml/NetworkingContentDelivery/VPCNATGateway.puml")
        lines.append("!include AWSPuml/NetworkingContentDelivery/VPCInternetGateway.puml")
        lines.append("!include AWSPuml/NetworkingContentDelivery/APIGateway.puml")
        lines.append("!include AWSPuml/NetworkingContentDelivery/Route53.puml")
        lines.append("!include AWSPuml/Groups/AWSCloud.puml")
        lines.append("!include AWSPuml/Groups/VPC.puml")
        lines.append("!include AWSPuml/Groups/PublicSubnet.puml")
        lines.append("!include AWSPuml/Groups/PrivateSubnet.puml")
        lines.append("!include AWSPuml/Groups/AvailabilityZone.puml")
        lines.append("")
        lines.append("hide stereotype")
        lines.append("skinparam linetype ortho")
        lines.append("")
        lines.append(f"title AWS Infrastructure - {account_topology.region}")
        lines.append("")
        
        for network_topology in account_topology.vpcs:
            lines.extend(self._generate_vpc_diagram_lines(network_topology))
        
        # Add routing table information as a table note
        if any(vpc.route_tables for vpc in account_topology.vpcs):
            lines.append("")
            lines.append("note bottom")
            lines.append("<size:12><b>Routing Tables</b></size>")
            lines.append("<#lightblue,#black>|= Route Table |= Destination |= Target |= Status |")
            
            for network_topology in account_topology.vpcs:
                for rt in network_topology.route_tables[:5]:  # Show first 5 route tables
                    rt_name = (rt.name or rt.resource_id)[:20]  # Truncate long names
                    for route in rt.routes[:3]:  # Show first 3 routes per table
                        dest = route.get('destination', 'N/A')[:18]
                        gateway = route.get('gateway_id', 'local')[:18]
                        status = route.get('state', 'active')[:10]
                        lines.append(f"| {rt_name} | {dest} | {gateway} | {status} |")
            lines.append("end note")
        
        lines.append("@enduml")
        return "\n".join(lines)
    
    def _generate_vpc_diagram_lines(self, topology: NetworkTopology) -> list:
        """Generate VPC diagram lines for PlantUML format using AWS Groups."""
        lines = []
        vpc_name = topology.vpc.name or topology.vpc.resource_id
        vpc_id = topology.vpc.resource_id.replace('-', '_')
        
        # Start with AWSCloud group containing the VPC
        lines.append(f"AWSCloudGroup(cloud_{vpc_id}) {{")
        lines.append(f"  VPCGroup({vpc_id}, \"{vpc_name}\") {{")
        
        # Add Internet Gateway
        igw_ids = []
        for igw in topology.internet_gateways:
            igw_id = igw.resource_id.replace('-', '_')
            igw_ids.append(igw_id)
            lines.append(f"    VPCInternetGateway({igw_id}, \"Internet Gateway\", \"\")")
        
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
        
        nat_gateway_ids = []
        ec2_ids = []
        
        # Generate AZ groups
        for az, subnet_groups in az_groups.items():
            az_id = az.replace('-', '_').replace('.', '_')
            lines.append(f"")
            lines.append(f"    AvailabilityZoneGroup({az_id}, \"\\t{az}\\t\") {{")
            
            # Public subnets in this AZ
            for subnet in subnet_groups['public']:
                subnet_id = subnet.resource_id.replace('-', '_')
                
                lines.append(f"      PublicSubnetGroup({subnet_id}, \"Public subnet\\n{subnet.cidr_block}\") {{")
                
                # NAT Gateways in this subnet
                nat_gateways = [nat for nat in topology.nat_gateways if nat.subnet_id == subnet.resource_id]
                for nat in nat_gateways:
                    nat_id = nat.resource_id.replace('-', '_')
                    nat_name = nat.name or "NAT Gateway"
                    nat_gateway_ids.append(nat_id)
                    lines.append(f"        VPCNATGateway({nat_id}, \"{nat_name}\", \"\") #Transparent")
                
                # EC2 instances in this subnet - organized in rows
                instances = topology.get_instances_by_subnet(subnet.resource_id)
                if instances:
                    # Group instances in rows of 3 for better layout
                    for i in range(0, len(instances), 3):
                        row_instances = instances[i:i+3]
                        row_instance_ids = []
                        for instance in row_instances:
                            instance_name = instance.name or "Instance"
                            instance_id = instance.resource_id.replace('-', '_')
                            ec2_ids.append(instance_id)
                            row_instance_ids.append(instance_id)
                            lines.append(f"        EC2Instance({instance_id}, \"{instance_name}\\n{instance.instance_type}\", \"\") #Transparent")
                        
                        # Add horizontal alignment for instances in the same row
                        if len(row_instance_ids) > 1:
                            for j in range(len(row_instance_ids) - 1):
                                lines.append(f"        {row_instance_ids[j]} -[hidden]r- {row_instance_ids[j+1]}")
                
                lines.append("      }")
            
            # Private subnets in this AZ
            for subnet in subnet_groups['private']:
                subnet_id = subnet.resource_id.replace('-', '_')
                
                lines.append(f"      PrivateSubnetGroup({subnet_id}, \"Private subnet\\n{subnet.cidr_block}\") {{")
                
                # EC2 instances in this subnet - organized in rows
                instances = topology.get_instances_by_subnet(subnet.resource_id)
                if instances:
                    # Group instances in rows of 3 for better layout
                    for i in range(0, len(instances), 3):
                        row_instances = instances[i:i+3]
                        row_instance_ids = []
                        for instance in row_instances:
                            instance_name = instance.name or "Instance"
                            instance_id = instance.resource_id.replace('-', '_')
                            ec2_ids.append(instance_id)
                            row_instance_ids.append(instance_id)
                            lines.append(f"        EC2Instance({instance_id}, \"{instance_name}\\n{instance.instance_type}\", \"\") #Transparent")
                        
                        # Add horizontal alignment for instances in the same row
                        if len(row_instance_ids) > 1:
                            for j in range(len(row_instance_ids) - 1):
                                lines.append(f"        {row_instance_ids[j]} -[hidden]r- {row_instance_ids[j+1]}")
                
                lines.append("      }")
            
            lines.append("    }")
        
        # Close VPC group
        lines.append("  }")
        lines.append("}")
        
        # Add Route53 zones outside the cloud group
        route53_ids = []
        for zone in topology.route53_zones:
            zone_id = zone.resource_id.replace('-', '_')
            zone_type = "Private" if zone.private_zone else "Public"
            route53_ids.append(zone_id)
            lines.append(f"Route53({zone_id}, \"{zone.zone_name}\\n{zone_type} Zone\", \"\")")
        
        # Add API Gateways outside the cloud group
        api_ids = []
        for api in topology.api_gateways:
            api_id = api.resource_id.replace('-', '_')
            api_ids.append(api_id)
            lines.append(f"APIGateway({api_id}, \"{api.api_name}\\n{api.api_type}\", \"\")")
        
        lines.append("")
        
        # Add network flow connections using proper PlantUML syntax
        if nat_gateway_ids and igw_ids:
            lines.append("' Network Flow Connections")
            for nat_id in nat_gateway_ids:
                lines.append(f"{nat_id} .u.> {igw_ids[0]}")
        
        # Connect private instances to NAT gateways
        if ec2_ids and nat_gateway_ids:
            # Find private subnet instances and connect them to NAT
            for az, subnet_groups in az_groups.items():
                for subnet in subnet_groups['private']:
                    instances = topology.get_instances_by_subnet(subnet.resource_id)
                    for instance in instances:
                        instance_id = instance.resource_id.replace('-', '_')
                        if nat_gateway_ids:
                            lines.append(f"{instance_id} .u.> {nat_gateway_ids[0]}")
        
        # Hide some connections to avoid clutter
        if len(nat_gateway_ids) > 1 and igw_ids:
            for nat_id in nat_gateway_ids[1:]:
                lines.append(f"{nat_id} .[hidden]u.> {igw_ids[0]}")
        
        
        lines.append("")
        return lines
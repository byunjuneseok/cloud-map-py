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
        lines.append("!include AWSPuml/Groups/Region.puml")
        lines.append("")
        lines.append("hide stereotype")
        lines.append("skinparam linetype ortho")
        lines.append("")
        lines.append(f"title AWS Infrastructure - {account_topology.region}")
        lines.append("")
        
        # Add AWS Cloud group containing Region
        region_id = account_topology.region.replace('-', '_')
        lines.append(f"AWSCloudGroup(aws_cloud) {{")
        lines.append(f"  RegionGroup({region_id}, \"{account_topology.region}\") {{")
        
        for network_topology in account_topology.vpcs:
            lines.extend(self._generate_vpc_diagram_lines(network_topology))
        
        lines.append("  }")
        lines.append("}")
        
        # Add routing table information as separate notes for each route table
        if any(vpc.route_tables for vpc in account_topology.vpcs):
            lines.append("")
            lines.append("' Routing Table Information")
            
            for network_topology in account_topology.vpcs:
                # Keep track of which subnets already have route table notes to distribute them
                used_subnets = set()
                
                for i, rt in enumerate(network_topology.route_tables[:5]):
                    rt_name = rt.name or rt.resource_id
                    
                    # Find subnets associated with this route table
                    associated_subnets = []
                    
                    # Check explicit associations first
                    if hasattr(rt, 'associations') and rt.associations:
                        for assoc in rt.associations:
                            if hasattr(assoc, 'subnet_id'):
                                for subnet in network_topology.subnets:
                                    if subnet.resource_id == assoc.subnet_id:
                                        associated_subnets.append(subnet)
                    
                    # If no explicit associations, try to distribute route tables across different subnets
                    if not associated_subnets:
                        # For main route table, associate with remaining subnets
                        if rt.name and 'main' in rt.name.lower():
                            for subnet in network_topology.subnets:
                                if subnet.resource_id not in used_subnets:
                                    associated_subnets.append(subnet)
                        else:
                            # For custom route tables, pick an unused subnet
                            available_subnets = [s for s in network_topology.subnets if s.resource_id not in used_subnets]
                            if available_subnets:
                                associated_subnets.append(available_subnets[0])
                            elif network_topology.subnets:
                                # If all subnets used, cycle through them
                                associated_subnets.append(network_topology.subnets[i % len(network_topology.subnets)])
                    
                    # If still no associations, use first available subnet
                    if not associated_subnets and network_topology.subnets:
                        available_subnets = [s for s in network_topology.subnets if s.resource_id not in used_subnets]
                        if available_subnets:
                            associated_subnets.append(available_subnets[0])
                        else:
                            associated_subnets.append(network_topology.subnets[0])
                    
                    # Create note for this route table on one of its associated subnets
                    if associated_subnets:
                        subnet = associated_subnets[0]  # Use first associated subnet
                        subnet_id = subnet.resource_id.replace('-', '_')
                        used_subnets.add(subnet.resource_id)
                        
                        lines.append(f"note top of {subnet_id}")
                        lines.append(f"<size:10><b>{rt_name}</b></size>")
                        lines.append("<#lightblue,#black>|= Destination |= Target |= Status |")
                        
                        for route in rt.routes[:3]:  # Show first 3 routes per table
                            dest = route.get('destination', 'N/A')[:15]
                            gateway = route.get('gateway_id', 'local')[:15] 
                            status = route.get('state', 'active')[:8]
                            lines.append(f"| {dest} | {gateway} | {status} |")
                        lines.append("end note")
        
        lines.append("@enduml")
        return "\n".join(lines)
    
    def _generate_vpc_diagram_lines(self, topology: NetworkTopology) -> list:
        """Generate VPC diagram lines for PlantUML format using AWS Groups."""
        lines = []
        vpc_name = topology.vpc.name or topology.vpc.resource_id
        vpc_id = topology.vpc.resource_id.replace('-', '_')
        
        # Add Internet Gateway outside VPC (at cloud level)
        igw_ids = []
        for igw in topology.internet_gateways:
            igw_id = igw.resource_id.replace('-', '_')
            igw_ids.append(igw_id)
            lines.append(f"      VPCInternetGateway({igw_id}, \"Internet Gateway\", \"\")")
        
        vpc_cidr = getattr(topology.vpc, 'cidr_block', 'N/A')
        lines.append(f"      VPCGroup({vpc_id}, \"{vpc_name}\\n{vpc_cidr}\") {{")
        
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
            lines.append(f"        AvailabilityZoneGroup({az_id}, \"\\t{az}\\t\") {{")
            
            # Public subnets in this AZ
            for subnet in subnet_groups['public']:
                subnet_id = subnet.resource_id.replace('-', '_')
                
                lines.append(f"          PublicSubnetGroup({subnet_id}, \"Public subnet\\n{subnet.cidr_block}\") {{")
                
                # NAT Gateways in this subnet
                nat_gateways = [nat for nat in topology.nat_gateways if nat.subnet_id == subnet.resource_id]
                for nat in nat_gateways:
                    nat_id = nat.resource_id.replace('-', '_')
                    nat_name = nat.name or "NAT Gateway"
                    nat_gateway_ids.append(nat_id)
                    lines.append(f"            VPCNATGateway({nat_id}, \"{nat_name}\", \"\") #Transparent")
                
                # EC2 instances in this subnet - organized in n x m grid
                instances = topology.get_instances_by_subnet(subnet.resource_id)
                if instances:
                    # Calculate optimal grid dimensions (prefer more square-like layout)
                    total_instances = len(instances)
                    if total_instances <= 2:
                        cols, rows = total_instances, 1
                    elif total_instances <= 4:
                        cols, rows = 2, (total_instances + 1) // 2
                    elif total_instances <= 9:
                        cols, rows = 3, (total_instances + 2) // 3
                    else:
                        # For larger numbers, aim for roughly square grid
                        cols = min(4, int(total_instances ** 0.5) + 1)
                        rows = (total_instances + cols - 1) // cols
                    
                    # Create grid layout
                    grid_instances = []
                    for row in range(rows):
                        row_instances = []
                        for col in range(cols):
                            idx = row * cols + col
                            if idx < total_instances:
                                instance = instances[idx]
                                instance_name = instance.name or "Instance"
                                instance_id = instance.resource_id.replace('-', '_')
                                ec2_ids.append(instance_id)
                                row_instances.append((instance_id, instance_name, instance.instance_type))
                                lines.append(f"            EC2Instance({instance_id}, \"{instance_name}\\n{instance.instance_type}\", \"\") #Transparent")
                            else:
                                row_instances.append(None)
                        grid_instances.append(row_instances)
                    
                    # Add horizontal connections within rows
                    for row_data in grid_instances:
                        valid_instances = [inst for inst in row_data if inst is not None]
                        if len(valid_instances) > 1:
                            for j in range(len(valid_instances) - 1):
                                lines.append(f"            {valid_instances[j][0]} -[hidden]r- {valid_instances[j+1][0]}")
                    
                    # Add vertical connections between rows
                    for row in range(len(grid_instances) - 1):
                        for col in range(cols):
                            if (grid_instances[row][col] is not None and 
                                grid_instances[row + 1][col] is not None):
                                lines.append(f"            {grid_instances[row][col][0]} -[hidden]d- {grid_instances[row + 1][col][0]}")
                
                lines.append("          }")
            
            # Private subnets in this AZ
            for subnet in subnet_groups['private']:
                subnet_id = subnet.resource_id.replace('-', '_')
                
                lines.append(f"          PrivateSubnetGroup({subnet_id}, \"Private subnet\\n{subnet.cidr_block}\") {{")
                
                # EC2 instances in this subnet - organized in n x m grid
                instances = topology.get_instances_by_subnet(subnet.resource_id)
                if instances:
                    # Calculate optimal grid dimensions (prefer more square-like layout)
                    total_instances = len(instances)
                    if total_instances <= 2:
                        cols, rows = total_instances, 1
                    elif total_instances <= 4:
                        cols, rows = 2, (total_instances + 1) // 2
                    elif total_instances <= 9:
                        cols, rows = 3, (total_instances + 2) // 3
                    else:
                        # For larger numbers, aim for roughly square grid
                        cols = min(4, int(total_instances ** 0.5) + 1)
                        rows = (total_instances + cols - 1) // cols
                    
                    # Create grid layout
                    grid_instances = []
                    for row in range(rows):
                        row_instances = []
                        for col in range(cols):
                            idx = row * cols + col
                            if idx < total_instances:
                                instance = instances[idx]
                                instance_name = instance.name or "Instance"
                                instance_id = instance.resource_id.replace('-', '_')
                                ec2_ids.append(instance_id)
                                row_instances.append((instance_id, instance_name, instance.instance_type))
                                lines.append(f"            EC2Instance({instance_id}, \"{instance_name}\\n{instance.instance_type}\", \"\") #Transparent")
                            else:
                                row_instances.append(None)
                        grid_instances.append(row_instances)
                    
                    # Add horizontal connections within rows
                    for row_data in grid_instances:
                        valid_instances = [inst for inst in row_data if inst is not None]
                        if len(valid_instances) > 1:
                            for j in range(len(valid_instances) - 1):
                                lines.append(f"            {valid_instances[j][0]} -[hidden]r- {valid_instances[j+1][0]}")
                    
                    # Add vertical connections between rows
                    for row in range(len(grid_instances) - 1):
                        for col in range(cols):
                            if (grid_instances[row][col] is not None and 
                                grid_instances[row + 1][col] is not None):
                                lines.append(f"            {grid_instances[row][col][0]} -[hidden]d- {grid_instances[row + 1][col][0]}")
                
                lines.append("          }")
            
            lines.append("        }")
        
        # Close VPC group
        lines.append("      }")
        
        # Add Route53 zones at cloud level
        route53_ids = []
        for zone in topology.route53_zones:
            zone_id = zone.resource_id.replace('-', '_')
            zone_type = "Private" if zone.private_zone else "Public"
            route53_ids.append(zone_id)
            lines.append(f"      Route53({zone_id}, \"{zone.zone_name}\\n{zone_type} Zone\", \"\")")
        
        # Add API Gateways at cloud level
        api_ids = []
        for api in topology.api_gateways:
            api_id = api.resource_id.replace('-', '_')
            api_ids.append(api_id)
            lines.append(f"      APIGateway({api_id}, \"{api.api_name}\\n{api.api_type}\", \"\")")
        
        lines.append("")
        
        # Add network flow connections using proper PlantUML syntax
        lines.append("' Network Flow Connections")
        
        # NAT Gateway to Internet Gateway flow
        if nat_gateway_ids and igw_ids:
            for nat_id in nat_gateway_ids:
                lines.append(f"{nat_id} .u.> {igw_ids[0]} : outbound traffic")
        
        # Public subnets to Internet Gateway flow  
        if igw_ids:
            for az, subnet_groups in az_groups.items():
                for subnet in subnet_groups['public']:
                    subnet_id = subnet.resource_id.replace('-', '_')
                    lines.append(f"{subnet_id} .u.> {igw_ids[0]} : direct internet access")
        
        # Private subnets to NAT gateways (subnet-level routing)
        if nat_gateway_ids:
            for az, subnet_groups in az_groups.items():
                for subnet in subnet_groups['private']:
                    subnet_id = subnet.resource_id.replace('-', '_')
                    # Find NAT gateway in same AZ if available, otherwise use first available
                    nat_in_same_az = None
                    for nat in topology.nat_gateways:
                        for pub_subnet in subnet_groups['public']:
                            if nat.subnet_id == pub_subnet.resource_id:
                                nat_in_same_az = nat.resource_id.replace('-', '_')
                                break
                        if nat_in_same_az:
                            break
                    
                    target_nat = nat_in_same_az if nat_in_same_az else nat_gateway_ids[0]
                    lines.append(f"{subnet_id} .d.> {target_nat} : outbound via NAT")
        
        # Hide some connections to avoid clutter
        if len(nat_gateway_ids) > 1 and igw_ids:
            for nat_id in nat_gateway_ids[1:]:
                lines.append(f"{nat_id} .[hidden]u.> {igw_ids[0]}")
        
        
        lines.append("")
        return lines
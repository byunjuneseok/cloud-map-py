"""Main executor for cloud map operations with multi-region and presentation support."""

import sys
import logging
from typing import List, Optional, Dict, Any
import boto3

from ..discovery.aws_network_discoverer import AWSNetworkDiscoverer
from ..discovery.aws_compute_discoverer import AWSComputeDiscoverer
from ..discovery.aws_serverless_discoverer import AWSServerlessDiscoverer
from ..discovery.aws_network_utilities_discoverer import AWSNetworkUtilitiesDiscoverer
from ..discovery.aws_database_discoverer import AWSDatabaseDiscoverer
from ..presentation.diagram import TextDiagramGenerator
from ..presentation.plantuml_generator import PlantUMLDiagramGenerator
from ..presentation.interfaces import DiagramGenerator
from ..model.enums import PresentationType
from .organizer import ResourceOrganizer
from .output_manager import OutputManager


class CloudMapExecutor:
    """Main executor for cloud infrastructure discovery and mapping with multi-region support."""
    
    def __init__(
        self,
        regions: List[str] = None,
        session: Optional[boto3.Session] = None,
        presentation_type: PresentationType = PresentationType.TERMINAL,
        command_args: Optional[Dict[str, Any]] = None
    ):
        self.regions = regions or ['us-east-1']
        self.session = session or boto3.Session()
        self.presentation_type = presentation_type
        self.command_args = command_args or {}
        self.organizer = ResourceOrganizer()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize output manager and create session directory
        self.output_manager = OutputManager()
        self.session_dir = self.output_manager.create_session_directory(self.command_args)
        
        # Initialize presentation layer
        self.diagram_generator = self._create_diagram_generator()
    
    def _create_diagram_generator(self) -> DiagramGenerator:
        """Create appropriate diagram generator based on presentation type."""
        if self.presentation_type == PresentationType.TERMINAL:
            return TextDiagramGenerator(self.output_manager, self.session_dir)
        elif self.presentation_type == PresentationType.PLANTUML:
            return PlantUMLDiagramGenerator(self.output_manager, self.session_dir)
        else:
            self.logger.warning(f"Unknown presentation type: {self.presentation_type}, using terminal")
            return TextDiagramGenerator(self.output_manager, self.session_dir)
    
    def discover_infrastructure(self, vpc_id: Optional[str] = None) -> Dict[str, Any]:
        """Discover infrastructure across all configured regions."""
        all_topologies = {}
        
        for region in self.regions:
            self.logger.info(f"Discovering infrastructure in region: {region}")
            
            try:
                topology = self._discover_region_infrastructure(region, vpc_id)
                all_topologies[region] = topology
                self.logger.info(f"Successfully discovered infrastructure in {region}")
            except Exception as e:
                self.logger.error(f"Failed to discover infrastructure in {region}: {e}")
                all_topologies[region] = None
        
        return all_topologies
    
    def _discover_region_infrastructure(self, region: str, vpc_id: Optional[str] = None):
        """Discover infrastructure for a specific region."""
        # Initialize discoverers for this region
        network_discoverer = AWSNetworkDiscoverer(region, self.session)
        compute_discoverer = AWSComputeDiscoverer(region, self.session)
        serverless_discoverer = AWSServerlessDiscoverer(region, self.session)
        utilities_discoverer = AWSNetworkUtilitiesDiscoverer(region, self.session)
        database_discoverer = AWSDatabaseDiscoverer(region, self.session)
        
        # Network discovery
        vpcs = network_discoverer.discover_vpcs()
        if vpc_id:
            vpcs = [vpc for vpc in vpcs if vpc.resource_id == vpc_id]
        
        all_subnets = []
        all_route_tables = []
        all_gateways = []
        all_nat_gateways = []
        all_network_acls = []
        all_security_groups = []
        
        for vpc in vpcs:
            subnets = network_discoverer.discover_subnets(vpc.resource_id)
            route_tables = network_discoverer.discover_route_tables(vpc.resource_id)
            gateways = network_discoverer.discover_internet_gateways(vpc.resource_id)
            nat_gateways = network_discoverer.discover_nat_gateways(vpc.resource_id)
            network_acls = network_discoverer.discover_network_acls(vpc.resource_id)
            security_groups = network_discoverer.discover_security_groups(vpc.resource_id)
            
            all_subnets.extend(subnets)
            all_route_tables.extend(route_tables)
            all_gateways.extend(gateways)
            all_nat_gateways.extend(nat_gateways)
            all_network_acls.extend(network_acls)
            all_security_groups.extend(security_groups)
        
        # Compute discovery
        ec2_instances = compute_discoverer.discover_ec2_instances()
        if vpc_id:
            ec2_instances = [inst for inst in ec2_instances if inst.vpc_id == vpc_id]
        
        # Serverless discovery
        lambda_functions = serverless_discoverer.discover_lambda_functions(vpc_id)
        
        # Network utilities discovery
        route53_zones = utilities_discoverer.discover_route53_zones(vpc_id)
        api_gateways = utilities_discoverer.discover_api_gateways(vpc_id)
        
        # Database discovery
        rds_instances = database_discoverer.discover_rds_instances(vpc_id)
        elasticache_clusters = database_discoverer.discover_elasticache_clusters(vpc_id)
        elasticache_replication_groups = database_discoverer.discover_elasticache_replication_groups(vpc_id)
        msk_clusters = database_discoverer.discover_msk_clusters(vpc_id)
        
        # Organization
        network_topologies = self.organizer.organize_network_topology(
            vpcs=vpcs,
            subnets=all_subnets,
            route_tables=all_route_tables,
            internet_gateways=all_gateways,
            nat_gateways=all_nat_gateways,
            network_acls=all_network_acls,
            security_groups=all_security_groups,
            ec2_instances=ec2_instances,
            lambda_functions=lambda_functions,
            route53_zones=route53_zones,
            api_gateways=api_gateways,
            rds_instances=rds_instances,
            elasticache_clusters=elasticache_clusters,
            elasticache_replication_groups=elasticache_replication_groups,
            msk_clusters=msk_clusters
        )
        
        account_topology = self.organizer.create_account_topology(
            region=region,
            network_topologies=network_topologies
        )
        
        return account_topology
    
    def generate_diagrams(self, topologies: Dict[str, Any], output_file: Optional[str] = None):
        """Generate diagrams for all discovered topologies."""
        # Always generate individual region diagrams first
        if output_file:
            with open(output_file, 'w') as f:
                self._write_diagrams(topologies, f)
        else:
            self._write_diagrams(topologies, sys.stdout)
        
        # Additionally generate consolidated diagram for multiple regions with PlantUML
        if (len(self.regions) > 1 and 
            self.presentation_type == PresentationType.PLANTUML and 
            len([t for t in topologies.values() if t is not None]) > 1):
            self._generate_consolidated_diagram(topologies, None)
    
    def _write_diagrams(self, topologies: Dict[str, Any], output):
        """Write diagrams to output stream."""
        for region, topology in topologies.items():
            if topology is None:
                output.write(f"No topology data for region: {region}\n\n")
                continue
            
            output.write(f"Region: {region}\n")
            output.write("=" * 50 + "\n")
            self.diagram_generator.generate_full_diagram(topology, output)
            output.write("\n")
    
    def execute(self, vpc_id: Optional[str] = None, output_file: Optional[str] = None):
        """Execute the full discovery and diagram generation process."""
        self.logger.info("Starting cloud map execution")
        self.logger.info(f"Session directory: {self.session_dir}")
        
        # Discover infrastructure
        topologies = self.discover_infrastructure(vpc_id)
        
        # Generate diagrams
        self.generate_diagrams(topologies, output_file)
        
        self.logger.info(f"Output saved to: {self.session_dir}")
        self.logger.info("Cloud map execution completed")
    
    def _generate_consolidated_diagram(self, topologies: Dict[str, Any], output_file: Optional[str] = None):
        """Generate a single consolidated diagram for multiple regions."""
        self.logger.info("Generating consolidated multi-region diagram")
        
        # Create consolidated content
        content = self._generate_consolidated_plantuml_content(topologies)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(content)
        else:
            sys.stdout.write(content)
        
        # Save to files and generate PNG if output manager is available
        if self.output_manager and self.session_dir:
            self.output_manager.save_consolidated_plantuml_output(content, self.session_dir, list(topologies.keys()))
    
    def _generate_consolidated_plantuml_content(self, topologies: Dict[str, Any]) -> str:
        """Generate consolidated PlantUML content for multiple regions."""
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
        lines.append("!include AWSPuml/Database/RDS.puml")
        lines.append("!include AWSPuml/Database/ElastiCache.puml")
        lines.append("!include AWSPuml/Analytics/ManagedStreamingforApacheKafka.puml")
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
        
        region_names = [region for region, topology in topologies.items() if topology is not None]
        lines.append(f"title AWS Multi-Region Infrastructure - {', '.join(region_names)}")
        lines.append("")
        
        # Add AWS Cloud group containing multiple regions
        lines.append(f"AWSCloudGroup(aws_cloud) {{")
        
        for region, topology in topologies.items():
            if topology is None:
                continue
                
            region_id = region.replace('-', '_')
            lines.append(f"  RegionGroup({region_id}, \"{region}\") {{")
            
            # Generate VPC content for this region using existing generator
            for network_topology in topology.vpcs:
                vpc_lines = self.diagram_generator._generate_vpc_diagram_lines(network_topology)
                # Adjust indentation for region grouping (add 2 more spaces)
                for line in vpc_lines:
                    if line.strip():
                        lines.append("  " + line)
            
            lines.append("  }")
        
        lines.append("}")
        lines.append("@enduml")
        return "\n".join(lines)
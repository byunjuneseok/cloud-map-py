"""Main orchestration module demonstrating SOLID principles."""

import sys
from typing import Optional
import boto3

from .aws_network_discoverer import AWSNetworkDiscoverer
from .aws_compute_discoverer import AWSComputeDiscoverer
from .aws_serverless_discoverer import AWSServerlessDiscoverer
from .aws_network_utilities_discoverer import AWSNetworkUtilitiesDiscoverer
from .organizer import ResourceOrganizer
from .diagram import TextDiagramGenerator


class CloudMapService:
    """Main service orchestrating cloud infrastructure discovery and mapping.
    
    Demonstrates SOLID principles:
    - Single Responsibility: Orchestrates the discovery process
    - Open/Closed: Extensible via dependency injection
    - Liskov Substitution: Uses abstract interfaces
    - Interface Segregation: Separate discoverer interfaces
    - Dependency Inversion: Depends on abstractions, not concretions
    """
    
    def __init__(
        self,
        region: str = 'us-east-1',
        session: Optional[boto3.Session] = None
    ):
        self.region = region
        self.session = session or boto3.Session()
        
        # Dependency injection - can be replaced with different implementations
        self.network_discoverer = AWSNetworkDiscoverer(region, session)
        self.compute_discoverer = AWSComputeDiscoverer(region, session)
        self.serverless_discoverer = AWSServerlessDiscoverer(region, session)
        self.utilities_discoverer = AWSNetworkUtilitiesDiscoverer(region, session)
        
        # Single responsibility components
        self.organizer = ResourceOrganizer()
        self.diagram_generator = TextDiagramGenerator()
    
    def discover_infrastructure(self, vpc_id: Optional[str] = None):
        """Discover all infrastructure components."""
        
        # Network discovery
        vpcs = self.network_discoverer.discover_vpcs()
        if vpc_id:
            vpcs = [vpc for vpc in vpcs if vpc.resource_id == vpc_id]
        
        all_subnets = []
        all_route_tables = []
        all_gateways = []
        
        for vpc in vpcs:
            subnets = self.network_discoverer.discover_subnets(vpc.resource_id)
            route_tables = self.network_discoverer.discover_route_tables(vpc.resource_id)
            gateways = self.network_discoverer.discover_internet_gateways(vpc.resource_id)
            
            all_subnets.extend(subnets)
            all_route_tables.extend(route_tables)
            all_gateways.extend(gateways)
        
        # Compute discovery
        ec2_instances = self.compute_discoverer.discover_ec2_instances()
        if vpc_id:
            ec2_instances = [inst for inst in ec2_instances if inst.vpc_id == vpc_id]
        
        # Serverless discovery
        lambda_functions = self.serverless_discoverer.discover_lambda_functions(vpc_id)
        
        # Network utilities discovery (for future use)
        # route53_zones = self.utilities_discoverer.discover_route53_zones(vpc_id)
        # api_gateways = self.utilities_discoverer.discover_api_gateways(vpc_id)
        
        # Organization
        network_topologies = self.organizer.organize_network_topology(
            vpcs=vpcs,
            subnets=all_subnets,
            route_tables=all_route_tables,
            internet_gateways=all_gateways,
            ec2_instances=ec2_instances,
            lambda_functions=lambda_functions
        )
        
        account_topology = self.organizer.create_account_topology(
            region=self.region,
            network_topologies=network_topologies
        )
        
        return account_topology
    
    def generate_diagram(self, account_topology, output_file: Optional[str] = None):
        """Generate infrastructure diagram."""
        
        if output_file:
            with open(output_file, 'w') as f:
                self.diagram_generator.generate_full_diagram(account_topology, f)
        else:
            self.diagram_generator.generate_full_diagram(account_topology, sys.stdout)


def main():
    """Entry point demonstrating the cloud mapping service."""
    
    # Example usage
    service = CloudMapService(region='ap-northeast-2')
    
    try:
        # Discover infrastructure
        topology = service.discover_infrastructure()
        
        # Generate diagram
        service.generate_diagram(topology)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
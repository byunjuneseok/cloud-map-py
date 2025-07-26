"""Main entry point for cloud map operations."""

import sys
import argparse
from typing import List, Optional

from ..model.enums import PresentationType
from .cloud_map_executor import CloudMapExecutor


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AWS Cloud Infrastructure Mapper")
    
    parser.add_argument(
        "--regions", 
        nargs='+', 
        default=['us-east-1'],
        help="AWS regions to scan (default: us-east-1)"
    )
    
    parser.add_argument(
        "--vpc-id",
        type=str,
        help="Specific VPC ID to analyze (optional)"
    )
    
    parser.add_argument(
        "--presentation",
        choices=['terminal', 'plantuml'],
        default='terminal',
        help="Presentation format (default: terminal)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (optional, defaults to stdout)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Convert presentation string to enum
    presentation_map = {
        'terminal': PresentationType.TERMINAL,
        'plantuml': PresentationType.PLANTUML
    }
    presentation_type = presentation_map[args.presentation]
    
    # Create command args for session tracking
    command_args = {
        'regions': args.regions,
        'presentation': args.presentation,
        'vpc_id': args.vpc_id,
        'output': args.output
    }
    
    # Create and configure executor
    executor = CloudMapExecutor(
        regions=args.regions,
        presentation_type=presentation_type,
        command_args=command_args
    )
    
    try:
        # Execute discovery and diagram generation
        executor.execute(vpc_id=args.vpc_id, output_file=args.output)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
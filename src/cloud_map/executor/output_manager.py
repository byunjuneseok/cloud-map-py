"""Output management for saving diagrams and files with proper organization."""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import boto3


class OutputManager:
    """Manages output directory structure and file saving."""
    
    def __init__(self, base_dir: str = "build"):
        self.base_dir = Path(base_dir)
        self.session_info = self._get_session_info()
    
    def _get_session_info(self) -> Dict[str, Any]:
        """Get session information for folder naming."""
        try:
            # Get AWS caller identity
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            user_id = identity.get('UserId', 'unknown')
            account = identity.get('Account', 'unknown')
            arn = identity.get('Arn', 'unknown')
            
            # Extract username from ARN
            username = 'unknown'
            if ':user/' in arn:
                username = arn.split(':user/')[-1]
            elif ':role/' in arn:
                username = arn.split(':role/')[-1]
            elif ':assumed-role/' in arn:
                username = arn.split(':assumed-role/')[-1].split('/')[0]
        except Exception:
            user_id = 'unknown'
            account = 'unknown'
            username = 'unknown'
        
        return {
            'user_id': user_id,
            'account': account,
            'username': username,
            'timestamp': datetime.now().strftime('%Y%m%d_%H%M%S')
        }
    
    def create_session_directory(self, command_args: Dict[str, Any]) -> Path:
        """Create a session directory based on timestamp and command info."""
        # Create folder name with timestamp and command info
        regions = '_'.join(command_args.get('regions', ['us-east-1']))
        presentation = command_args.get('presentation', 'terminal')
        vpc_id = command_args.get('vpc_id') or 'all-vpcs'
        
        folder_name = (
            f"{self.session_info['timestamp']}_"
            f"{self.session_info['account']}_"
            f"{presentation}_"
            f"{regions}_"
            f"{vpc_id}"
        )
        
        session_dir = self.base_dir / folder_name
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Save session metadata
        metadata = {
            'session_info': self.session_info,
            'command_args': command_args,
            'execution_time': datetime.now().isoformat()
        }
        
        with open(session_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return session_dir
    
    def save_plantuml_output(self, content: str, session_dir: Path, region: str) -> Dict[str, Path]:
        """Save PlantUML content and render to image."""
        files = {}
        
        # Save .puml file
        puml_file = session_dir / f"{region}_infrastructure.puml"
        with open(puml_file, 'w') as f:
            f.write(content)
        files['puml'] = puml_file
        
        # Try to render to PNG using plantuml
        try:
            png_file = session_dir / f"{region}_infrastructure.png"
            result = subprocess.run([
                'plantuml', '-tpng', str(puml_file)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and png_file.exists():
                files['png'] = png_file
            else:
                # Try with java -jar if plantuml command failed
                try:
                    result = subprocess.run([
                        'java', '-jar', '/usr/local/bin/plantuml.jar', '-tpng', 
                        str(puml_file)
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0 and png_file.exists():
                        files['png'] = png_file
                except Exception:
                    pass
                    
        except Exception as e:
            # Create a note about rendering failure
            with open(session_dir / f"{region}_render_error.txt", 'w') as f:
                f.write(f"PlantUML rendering failed: {e}\n")
                f.write("Install PlantUML to enable image generation:\n")
                f.write("brew install plantuml  # macOS\n")
                f.write("apt-get install plantuml  # Ubuntu\n")
        
        return files
    
    def save_consolidated_plantuml_output(self, content: str, session_dir: Path, regions: list) -> Dict[str, Path]:
        """Save consolidated PlantUML content for multiple regions and render to PNG."""
        files = {}
        
        # Create filename for multi-region diagram
        region_str = '_'.join(regions)
        
        # Save .puml file
        puml_file = session_dir / f"multi_region_{region_str}_infrastructure.puml"
        with open(puml_file, 'w') as f:
            f.write(content)
        files['puml'] = puml_file
        
        # Try to render to PNG using plantuml
        try:
            png_file = session_dir / f"multi_region_{region_str}_infrastructure.png"
            result = subprocess.run([
                'plantuml', '-tpng', str(puml_file)
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and png_file.exists():
                files['png'] = png_file
                print(f"Multi-region PNG diagram generated: {png_file}")
            else:
                # Try with java -jar if plantuml command failed
                try:
                    result = subprocess.run([
                        'java', '-jar', '/usr/local/bin/plantuml.jar', '-tpng', 
                        str(puml_file)
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and png_file.exists():
                        files['png'] = png_file
                        print(f"Multi-region PNG diagram generated: {png_file}")
                except Exception:
                    pass
                    
        except Exception as e:
            # Create a note about rendering failure
            with open(session_dir / f"multi_region_render_error.txt", 'w') as f:
                f.write(f"PlantUML rendering failed: {e}\n")
                f.write("Install PlantUML to enable image generation:\n")
                f.write("brew install plantuml  # macOS\n")
                f.write("apt-get install plantuml  # Ubuntu\n")
        
        return files
    
    def save_terminal_output(self, content: str, session_dir: Path, region: str) -> Path:
        """Save terminal output to text file."""
        output_file = session_dir / f"{region}_infrastructure.txt"
        with open(output_file, 'w') as f:
            f.write(content)
        return output_file
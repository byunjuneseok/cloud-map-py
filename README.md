# cloud-map-py

AWS Cloud Infrastructure Mapper - Visualize and analyze AWS cloud resources

## Installation

```bash
pip install cloud-map-py
```

## Usage

### Basic Usage

```bash
cloud-map --regions us-east-1 --presentation terminal
```

### PlantUML Diagram Generation

```bash
cloud-map --regions ap-northeast-2 --presentation plantuml --output infrastructure.puml
```

### Multiple Regions

```bash
cloud-map --regions us-east-1 us-west-2 eu-west-1 --presentation plantuml
```

When multiple regions are specified with PlantUML presentation, the tool automatically generates a single consolidated diagram showing all regions in one PNG image.

### Specific VPC Analysis

```bash
cloud-map --vpc-id vpc-12345678 --presentation plantuml
```

## Options

- `--regions`: AWS regions to scan (default: us-east-1)
- `--vpc-id`: Specific VPC ID to analyze (optional)
- `--presentation`: Output format - `terminal` or `plantuml` (default: terminal)
- `--output`: Output file path (optional, defaults to stdout)

## Requirements

- Python 3.12+
- AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
- Appropriate AWS permissions for EC2, Lambda, Route53, API Gateway services

## Development

```bash
git clone https://github.com/your-username/cloud-map-py.git
cd cloud-map-py
uv install --dev
uv run cloud-map --help
```

## License

MIT

# Cloud Map Python - Tasks

## Completed Tasks
- [x] Set up project structure with boto3 and mypy dependencies
- [x] Implement network discovery (VPC, subnet, routing, IGW)
- [x] Implement computing resources discovery (EC2) with network info
- [x] Create organization layer for networks and computing resources
- [x] Implement diagram generation from subnet to account level
- [x] Add serverless product discovery (Lambda, etc.)
- [x] Map serverless resources to appropriate subnets
- [x] Ensure SOLID principles throughout implementation
- [x] Implement network utilities discovery (Route53, API Gateway)

## Refactor Tasks

### High Priority
- [x] Split modules into discovery, model, executor, presentation packages
- [x] Implement boto3 caller abstraction layer
- [x] Add logging for all API calls in boto3 caller

### Medium Priority
- [x] Create executor that can choose presentation layer (terminal/PlantUML/diagrams)
- [x] Add multi-region support to executor

### Low Priority
- [x] Define enums for constants throughout codebase
- [x] Research and recommend additional presentation options
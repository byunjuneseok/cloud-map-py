"""Enums for cloud map constants."""

from enum import Enum


class PresentationType(Enum):
    """Enum for presentation layer types."""
    TERMINAL = "terminal"
    PLANTUML = "plantuml"


class ResourceState(Enum):
    """Enum for AWS resource states."""
    AVAILABLE = "available"
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"
    STOPPING = "stopping"
    STARTING = "starting"
    TERMINATED = "terminated"
    TERMINATING = "terminating"


class InstanceType(Enum):
    """Common EC2 instance types."""
    T2_MICRO = "t2.micro"
    T2_SMALL = "t2.small"
    T2_MEDIUM = "t2.medium"
    T3_MICRO = "t3.micro"
    T3_SMALL = "t3.small"
    T3_MEDIUM = "t3.medium"
    M5_LARGE = "m5.large"
    M5_XLARGE = "m5.xlarge"
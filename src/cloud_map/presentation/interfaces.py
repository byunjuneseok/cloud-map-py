"""Presentation layer interfaces."""

from abc import ABC, abstractmethod
from typing import TextIO, Any


class DiagramGenerator(ABC):
    """Abstract base class for diagram generation."""
    
    @abstractmethod
    def generate_full_diagram(self, account_topology: Any, output: TextIO) -> None:
        """Generate a full diagram of the account topology."""
        pass
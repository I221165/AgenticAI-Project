from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel

class BaseAgenticTool(ABC):
    """
    Base interface for all tools in the MCP (Model Context Protocol) Layer.
    Tools should implement this interface so they can be registered and executed
    by the agents dynamically.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """A description of what the tool does and when to use it."""
        pass
        
    @property
    @abstractmethod
    def args_schema(self) -> type[BaseModel]:
        """The Pydantic schema for the tool's input arguments."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """
        Executes the tool with the provided arguments.
        The arguments should match the args_schema.
        """
        pass
        
    def to_langchain_tool(self):
        """
        Converts this base tool into a LangChain StructuredTool, 
        making it compatible with LangGraph agents.
        """
        from langchain_core.tools import StructuredTool
        return StructuredTool.from_function(
            func=self.execute,
            name=self.name,
            description=self.description,
            args_schema=self.args_schema,
        )

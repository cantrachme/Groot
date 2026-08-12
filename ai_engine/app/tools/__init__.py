from .health import HealthCheckTool
from .registry import ToolRegistry


tool_registry = ToolRegistry()
tool_registry.register(HealthCheckTool())

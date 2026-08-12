from .tool import Tool


class HealthCheckTool(Tool):
    name = "health_check"
    description = "Check whether the GROOT AI engine is operational."

    def execute(self, **kwargs) -> object:
        return {
            "status": "healthy",
            "service": "groot-ai-engine",
        }

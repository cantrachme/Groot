from .registry import ToolRegistry


def build_tool_schemas(registry: ToolRegistry) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters_model.model_json_schema()
                if getattr(tool, "parameters_model", None) is not None
                else {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            },
        }
        for tool in (
            registry.get(name)
            for name in registry.list()
        )
    ]

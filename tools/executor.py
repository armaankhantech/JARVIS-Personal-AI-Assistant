
class ToolExecutor:
    def __init__(self, registry):
        self.registry = registry

    def execute(self, tool_name, arguments=None):
        tool = self.registry.get(tool_name)

        if tool is None:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' is not registered.",
            }

        if arguments is None:
            arguments = {}

        if not isinstance(arguments, dict):
            return {
                "success": False,
                "error": "Tool arguments must be a dictionary.",
            }

        try:
            result = tool["function"](**arguments)

            # Preserve a tool's explicit success or failure result.
            if isinstance(result, dict) and "success" in result:
                return result

            # Only treat a normal return value as success.
            return {
                "success": True,
                "result": result,
            }

        except Exception as error:
            return {
                "success": False,
                "error": f"{type(error).__name__}: {error}",
            }
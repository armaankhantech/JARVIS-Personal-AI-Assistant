"""Small explicit registry for tools that Jarvis is allowed to execute."""


class ToolRegistry:
    """Register and retrieve callable Jarvis tools by stable name."""

    def __init__(self):
        self.tools = {}

    def register(self, name, function, description):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Tool name must be a non-empty string.")
        if not callable(function):
            raise TypeError(f"Tool '{name}' must be callable.")
        if not isinstance(description, str) or not description.strip():
            raise TypeError("Tool description must be a non-empty string.")
        name = name.strip()
        if name in self.tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        self.tools[name] = {"function": function, "description": description.strip()}

    def get(self, name):
        return self.tools.get(name)

    def list_tools(self):
        return self.tools

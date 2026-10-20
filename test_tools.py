from tools.registry import ToolRegistry
from tools.basic_tools import get_time
from tools.executor import ToolExecutor


registry = ToolRegistry()

registry.register(
    "get_time",
    get_time,
    "Get the current local time"
)

executor = ToolExecutor(registry)


print("\n========================================")
print("       JARVIS TOOL EXECUTOR TEST")
print("========================================")

print("\nAvailable tools:")
print(registry.list_tools().keys())

print("\nExecuting get_time...")

result = executor.execute("get_time")

print("\nTool result:")
print(result)

print("========================================")
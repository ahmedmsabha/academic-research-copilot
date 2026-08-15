"""Tool-layer errors. Services map these to user-safe chat replies."""


class ToolError(Exception):
    def __init__(self, message: str, *, code: str = "TOOL_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

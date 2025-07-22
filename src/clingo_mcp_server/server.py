"""
ASP ModelContextProtocol Server
Exposes an MCP server that executes ASP code using clingo.
"""
from collections import defaultdict
from mcp.server.fastmcp import FastMCP
import clingo
from typing import Dict, Optional

# In-memory virtual file manager
class VirtualFileManager:
    def __init__(self):
        self.files: Dict[str, list[str]] = defaultdict(list)

    def create_file(self, name: str) -> None:
        self.files[name] = []

    def append_to_file(self, name: str, content: str) -> None:
        if name not in self.files:
            self.create_file(name)
        self.files[name].append(content)

    def undo_append(self, name: str) -> None:
        if name in self.files and self.files[name]:
            self.files[name].pop()

    def get_content(self, name: str) -> Optional[str]:
        if name not in self.files:
            return None
        return "".join(self.files.get(name, []))

    def list_files(self):
        return list(self.files.keys())
    
    def write_file_to_disk(self, name: str) -> None:
        """Write the content of a virtual file to disk."""
        with open(name, 'w') as f:
            f.write(self.get_content(name))

# Singleton file manager
vfs = VirtualFileManager()

mcp = FastMCP("clingo")

@mcp.tool()
def create_virtual_file(filename: str) -> dict:
    """Create a new virtual file (overwrites if exists)."""
    try:
        vfs.create_file(filename)
        return {"result": f"File '{filename}' created."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def append_to_virtual_file(filename: str, content: str) -> dict:
    """Append content to a virtual file."""
    try:
        vfs.append_to_file(filename, content)
        content = vfs.get_content(filename)
        return {
            "result": f"Appended to '{filename}'.",
            "content": content
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def undo_append_to_virtual_file(filename: str) -> dict:
    """Undo the last append operation on a virtual file."""
    try:
        vfs.undo_append(filename)
        return {"result": f"Last append undone for '{filename}'."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_virtual_file_content(filename: str) -> dict:
    """Get the current content of a virtual file."""
    try:
        content = vfs.get_content(filename)
        if content is None:
            return {"error": f"File '{filename}' does not exist."}
        return {"content": content}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def list_virtual_files() -> dict:
    """List all virtual files."""
    try:
        files = vfs.list_files()
        return {"files": files}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def write_virtual_file_to_disk(filename: str) -> dict:
    """Write the content of a virtual file to disk."""
    try:
        vfs.write_file_to_disk(filename)
        return {"result": f"File '{filename}' written to disk."}
    except Exception as e:
        return {"error": str(e)}

### TODO: number parts of the files, be accesible by indexes. Then you can remove or change
### parts of the encoding without rewriting the whole file.
### Also allow to inspect ground rules (maybe sample) of single parts of the file.
@mcp.tool()
def check_syntax(filenames: list[str]) -> dict:
    """Check syntax of a virtual file using clingo."""
    ctl = clingo.Control()
    for filename in filenames:
        content = vfs.get_content(filename)
        if content is None:
            return {"error": f"File '{filename}' does not exist."}
        try:
            ctl.add("base", [], content)
            ctl.ground([("base", [])])
        except Exception as e:
            return {"error": f"Syntax error: {e}"}
    return {"result": "Syntax OK"}

@mcp.tool()
def run_clingo(filenames: list[str], max_models: int = 1) -> dict:
    """Run clingo on the virtual file and return the output.
    max_models: Maximum number of models to return, 0 means all models."""
    if not filenames:
        return {"error": "No files provided."}
    ctl = clingo.Control(["--models", str(max_models)])
    for f in filenames:
        content = vfs.get_content(f)
        if content is None:
            return {"error": f"File '{f}' does not exist."}
        ctl.add("base", [], content)
    try:
        ctl.ground([("base", [])])
        models = {}
        with ctl.solve(yield_ = True) as handle:
            for model in handle:
                models[f"Answer {model.number}"] = [str(atom) for atom in model.symbols(shown=True)]
        if not models:
            return {"result": "UNSATISFIABLE"}
        return {"models": models}
    except Exception as e:
        return {"error": f"Error running clingo: {e}"}


def main():
    mcp.run()

# Entry point for console_scripts
def main():
    mcp.run()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

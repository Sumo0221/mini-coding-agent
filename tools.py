"""
tools.py - Tool Implementations

Implements tools for the coding agent:
- BashTool: Execute shell commands (with cross-platform support)
- ReadTool: Read file contents
- WriteTool: Write file contents
- EditTool: Edit files (with regex support)
- WebSearchTool: Search the web using SearXNG
- WebFetchTool: Fetch web page content
- PythonREPLTool: Execute Python code
"""

import os
import re
import sys
import json
import subprocess
import shutil
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from platform_utils import (
    translate_command, get_translator, is_windows,
    safe_encode_for_output, get_safe_encoding
)


class Tool(ABC):
    """Abstract base class for tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for function calling."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for the LLM."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON schema for tool parameters."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool with given parameters."""
        pass

    def to_openai_function(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class BashTool(Tool):
    """
    Execute shell commands with cross-platform support.
    
    Automatically translates Unix commands to Windows equivalents
    and handles encoding issues for non-ASCII output.
    """

    def __init__(self, allow_translation: bool = True):
        """
        Initialize BashTool.
        
        Args:
            allow_translation: If True, automatically translate Unix commands
                              to Windows equivalents (default: True)
        """
        self.allow_translation = allow_translation
        self._translator = get_translator() if allow_translation else None

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return """Execute a bash/shell command and return the output. 
Use this to run terminal commands like ls, cd, git, python, etc.
Automatically translates Unix commands to Windows equivalents on Windows."""

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute (Unix or Windows)"
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory for the command"
                },
                "translate": {
                    "type": "boolean",
                    "description": "Whether to translate Unix commands to Windows (default: auto-detect)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds (default: 30)"
                }
            },
            "required": ["command"]
        }

    def _translate_if_needed(self, command: str) -> str:
        """Translate command if needed and on Windows."""
        if not self.allow_translation or not self._translator:
            return command
        
        translated, was_translated = self._translator.translate(command)
        if was_translated and is_windows():
            # Add a remark about translation (using REM for Windows cmd.exe compatibility)
            return f"REM Translated from: {command}\n{translated}"
        return command

    def execute(self, command: str, working_dir: Optional[str] = None, 
                translate: Optional[bool] = None, timeout: int = 30) -> str:
        """
        Execute a shell command with comprehensive error handling.
        
        Args:
            command: The shell command to execute
            working_dir: Optional working directory
            translate: Override auto-translation setting
            timeout: Command timeout in seconds
        """
        # Validate command input
        if not command or not command.strip():
            return "Error: Empty command provided. Please provide a valid shell command."
        
        command = command.strip()
        
        # Validate working directory if provided
        if working_dir:
            if not os.path.exists(working_dir):
                return f"Error: Working directory does not exist: {working_dir}"
            if not os.path.isdir(working_dir):
                return f"Error: Working directory path is not a directory: {working_dir}"
        
        # Apply translation if needed
        should_translate = translate if translate is not None else self.allow_translation
        if should_translate and is_windows():
            command = self._translate_if_needed(command)

        try:
            # Determine shell based on OS
            if os.name == "nt":  # Windows
                # Use cmd.exe for Windows
                shell = ["cmd", "/c"]
            else:  # Unix-like
                shell = ["/bin/sh", "-c"]

            # Build the full command
            if is_windows() and should_translate:
                # For translated commands, execute directly
                full_command = command
            else:
                full_command = " ".join(shell) + f' "{command}"'

            # Set up environment
            env = os.environ.copy()
            
            # Try to set encoding for Python subprocess
            if is_windows():
                # Set console encoding to UTF-8 if possible
                env["PYTHONIOENCODING"] = "utf-8"
                # Set chcp to UTF-8 (code page 65001)
                full_command = f'chcp 65001 >nul && {command}'

            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                env=env,
                errors="replace"  # Handle encoding errors gracefully
            )

            # Process output with safe encoding
            output = self._process_output(result)
            
            # Build output message
            if result.returncode == 0:
                # Success case
                if output["stdout"]:
                    return output["stdout"]
                elif output["stderr"]:
                    # Some commands output to stderr even on success (e.g., warnings)
                    return f"Command executed successfully (output on stderr):\n{output['stderr']}"
                else:
                    return "Command executed successfully (no output)"
            else:
                # Failure case - include helpful context
                error_msg_parts = [f"Command failed with exit code {result.returncode}"]
                
                # Try to provide hints for common error codes
                if result.returncode == 127:
                    error_msg_parts.append("(Command not found - check the command name and PATH)")
                elif result.returncode == 126:
                    error_msg_parts.append("(Permission denied or command not executable)")
                elif result.returncode == 1:
                    error_msg_parts.append("(General error)")
                elif result.returncode == 2:
                    error_msg_parts.append("(Misuse of shell command)")
                
                if output["stdout"]:
                    error_msg_parts.append(f"\nSTDOUT:\n{output['stdout']}")
                if output["stderr"]:
                    error_msg_parts.append(f"\nSTDERR:\n{output['stderr']}")
                
                return "\n".join(error_msg_parts)

        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds.\nAttempted command: {command}"
        except PermissionError as e:
            return f"Error: Permission denied when executing command.\nDetails: {str(e)}\nCommand: {command}"
        except FileNotFoundError as e:
            return f"Error: Command or executable not found.\nDetails: {str(e)}\nCommand: {command}"
        except OSError as e:
            return f"Error: OS error occurred while executing command.\nDetails: {str(e)}\nCommand: {command}"
        except Exception as e:
            return f"Error executing command: {str(e)}\nCommand: {command}"

    def _process_output(self, result: subprocess.CompletedProcess) -> Dict[str, str]:
        """Process command output with safe encoding."""
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        
        # Try to fix encoding issues on Windows
        if is_windows():
            try:
                # Try to re-encode with UTF-8
                if stdout:
                    stdout = stdout.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
                if stderr:
                    stderr = stderr.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
            except Exception:
                # Fallback to raw output with replacement
                pass
        
        return {
            "stdout": stdout.strip(),
            "stderr": stderr.strip()
        }


class ReadTool(Tool):
    """Read file contents."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file. Returns the file content or an error message if the file cannot be read."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Path to the file to read"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (0 = all)"
                },
                "offset": {
                    "type": "integer",
                    "description": "Line offset to start reading from (1-indexed)"
                }
            },
            "required": ["filename"]
        }

    def execute(self, filename: str, max_lines: int = 0, offset: int = 0) -> str:
        """Read a file."""
        try:
            if not os.path.exists(filename):
                return f"Error: File not found: {filename}"

            # Try UTF-8 first, then fall back to other encodings
            content = None
            encodings = ["utf-8", "utf-8-sig", "cp950", "big5", "gb2312", "latin-1"]
            
            for encoding in encodings:
                try:
                    with open(filename, "r", encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                # Last resort: binary read with replacement
                with open(filename, "rb") as f:
                    raw = f.read()
                content = raw.decode("utf-8", errors="replace")

            # Apply offset and max_lines
            lines = content.split("\n")
            if offset > 0:
                lines = lines[offset:]
            if max_lines > 0:
                lines = lines[:max_lines]
            content = "\n".join(lines)

            if not content:
                return "(Empty file)"

            # Truncate if too long
            max_chars = 10000
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n... (truncated, total {len(content)} chars)"

            return content

        except Exception as e:
            return f"Error reading file: {str(e)}"


class WriteTool(Tool):
    """Write file contents."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Create or overwrite a file with the given content. Creates parent directories if needed."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                },
                "append": {
                    "type": "boolean",
                    "description": "If true, append to existing file instead of overwriting"
                }
            },
            "required": ["filename", "content"]
        }

    def execute(self, filename: str, content: str, append: bool = False) -> str:
        """Write content to a file."""
        try:
            # Create parent directories if needed
            parent_dir = os.path.dirname(filename)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            mode = "a" if append else "w"
            with open(filename, mode, encoding="utf-8") as f:
                f.write(content)

            action = "Appended to" if append else "Written to"
            return f"Success: {action} file: {filename}"

        except Exception as e:
            return f"Error writing file: {str(e)}"


class EditTool(Tool):
    """
    Edit file contents with advanced matching options.
    
    Supports:
    - Exact string matching (default)
    - Regex pattern matching (with regex=True)
    - Fuzzy matching (with fuzzy=True)
    """

    def __init__(self):
        self._fuzzy_threshold = 0.8  # 80% similarity threshold

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return """Edit a file by replacing text.
Supports:
- Exact match (default): old_string must match exactly
- Regex match: Use regex=True and old_string as a regex pattern
- Fuzzy match: Use fuzzy=True for approximate matching (threshold 80%)"""

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Path to the file to edit"
                },
                "old_string": {
                    "type": "string",
                    "description": "Text to find and replace (exact match or regex pattern)"
                },
                "new_string": {
                    "type": "string",
                    "description": "Replacement text"
                },
                "regex": {
                    "type": "boolean",
                    "description": "If true, treat old_string as a regex pattern (default: false)"
                },
                "fuzzy": {
                    "type": "boolean",
                    "description": "If true, use fuzzy matching (default: false)"
                },
                "all_matches": {
                    "type": "boolean",
                    "description": "If true, replace all occurrences (default: false, replaces only first)"
                }
            },
            "required": ["filename", "old_string", "new_string"]
        }

    def execute(
        self,
        filename: str,
        old_string: str,
        new_string: str,
        regex: bool = False,
        fuzzy: bool = False,
        all_matches: bool = False
    ) -> str:
        """Edit a file with various matching strategies."""
        try:
            if not os.path.exists(filename):
                return f"Error: File not found: {filename}"

            # Read file content
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Try other encodings
                content = None
                for encoding in ["cp950", "big5", "gb2312", "latin-1"]:
                    try:
                        with open(filename, "r", encoding=encoding) as f:
                            content = f.read()
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    with open(filename, "rb") as f:
                        raw = f.read()
                    content = raw.decode("utf-8", errors="replace")

            # Find and replace based on mode
            if regex:
                return self._edit_regex(content, filename, old_string, new_string, all_matches)
            elif fuzzy:
                return self._edit_fuzzy(content, filename, old_string, new_string, all_matches)
            else:
                return self._edit_exact(content, filename, old_string, new_string, all_matches)

        except Exception as e:
            return f"Error editing file: {str(e)}"

    def _edit_exact(self, content: str, filename: str, old_string: str, 
                    new_string: str, all_matches: bool) -> str:
        """Edit with exact string matching."""
        if old_string not in content:
            return f"Error: old_string not found in '{filename}'.\nExact text to find:\n{old_string}"
        
        count = content.count(old_string)
        if count > 1 and not all_matches:
            return f"Error: old_string appears {count} times in '{filename}'.\nUse all_matches=true to replace all occurrences."
        
        if all_matches:
            new_content = content.replace(old_string, new_string)
            count = count  # Already counted
        else:
            new_content = content.replace(old_string, new_string, 1)
            count = 1

        with open(filename, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return f"Success: Replaced {count} occurrence(s) in {filename}"

    def _edit_regex(self, content: str, filename: str, pattern: str, 
                    new_string: str, all_matches: bool) -> str:
        """Edit with regex pattern matching."""
        try:
            if all_matches:
                new_content, count = re.subn(pattern, new_string, content)
            else:
                new_content, count = re.subn(pattern, new_string, content, count=1)
            
            if count == 0:
                return f"Error: Regex pattern not found in '{filename}'.\nPattern: {pattern}"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            return f"Success: Replaced {count} regex match(es) in {filename}"
        
        except re.error as e:
            return f"Error: Invalid regex pattern: {str(e)}"

    def _edit_fuzzy(self, content: str, filename: str, old_string: str, 
                    new_string: str, all_matches: bool) -> str:
        """Edit with fuzzy matching."""
        lines = content.split("\n")
        old_lines = old_string.split("\n") if "\n" in old_string else [old_string]
        new_lines = new_string.split("\n") if "\n" in new_string else [new_string]
        
        matches_found = []
        
        for i in range(len(lines) - len(old_lines) + 1):
            # Check each possible starting position
            match = True
            for j in range(len(old_lines)):
                similarity = self._similarity(lines[i + j], old_lines[j])
                if similarity < self._fuzzy_threshold:
                    match = False
                    break
            
            if match:
                matches_found.append(i)
        
        if not matches_found:
            return f"Error: No fuzzy match found for:\n{old_string}\n(Try lowering threshold or using exact/regex mode)"
        
        if len(matches_found) > 1 and not all_matches:
            return f"Error: old_string fuzzy matches {len(matches_found)} locations.\nUse all_matches=true to replace all."
        
        # Perform replacements
        offset = 0
        for start_idx in matches_found:
            for j in range(len(old_lines)):
                lines[start_idx + j - offset] = new_lines[j] if j < len(new_lines) else new_string
            offset += len(old_lines) - 1
        
        new_content = "\n".join(lines)
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return f"Success: Replaced {len(matches_found)} fuzzy match(es) in {filename}"

    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (simple Jaccard-based)."""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        # Simple character-based similarity
        set1 = set(s1.lower())
        set2 = set(s2.lower())
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 1.0 if s1 == s2 else 0.0
        
        return intersection / union


class WebSearchTool(Tool):
    """
    Search the web using SearXNG with fallback to OpenClaw's built-in search.
    
    Dual保障機制：
    1. 第一優先：本地 SearXNG (預設 http://localhost:8888)
    2. 第二優先：OpenClaw 內建 web_search (Tavily 等)
    3. 最終：web_fetch 直接抓取
    """

    # SearXNG instances to try (in order of preference)
    SEARXNG_URLS = [
        "http://localhost:8888",  # Docker mapping
        "http://localhost:8080",  # Direct SearXNG
    ]

    def __init__(self):
        """Initialize WebSearchTool with dual保障."""
        self._searxng_url = None
        self._available = None  # Cache availability check

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return """Search the web for information using dual保障:
1. Primary: Local SearXNG instance (http://localhost:8888)
2. Fallback: OpenClaw built-in web search
3. Final: Direct web fetch

Returns search results with titles, URLs, and descriptions."""

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                },
                "count": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10, max: 50)"
                },
                "engines": {
                    "type": "string",
                    "description": "Comma-separated list of search engines to use (optional, SearXNG only)"
                }
            },
            "required": ["query"]
        }

    def _find_available_searxng(self) -> Optional[str]:
        """Find an available SearXNG instance."""
        for url in self.SEARXNG_URLS:
            try:
                req = urllib.request.Request(
                    f"{url}/search?q=test&format=json",
                    method="GET"
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        return url
            except Exception:
                continue
        return None

    def _search_searxng(self, query: str, count: int, engines: Optional[str] = None) -> Optional[str]:
        """Try to search using local SearXNG. Returns None if unavailable."""
        searxng_url = self._find_available_searxng()
        if not searxng_url:
            return None
        
        count = min(max(1, count), 50)
        
        try:
            params = {
                "q": query,
                "format": "json",
                "limit": count
            }
            
            if engines:
                params["engines"] = engines
            
            query_string = urllib.parse.urlencode(params)
            url = f"{searxng_url}/search?{query_string}"
            
            req = urllib.request.Request(url, method="GET")
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            
            if not result.get("results"):
                return None
            
            results = result["results"][:count]
            
            output_parts = [f"[SearXNG] Search results for: {query}\n"]
            output_parts.append("=" * 50 + "\n")
            
            for i, item in enumerate(results, 1):
                title = item.get("title", "No title")
                item_url = item.get("url", "No URL")
                desc = item.get("content", item.get("description", "No description"))
                
                output_parts.append(f"{i}. {title}")
                output_parts.append(f"   URL: {item_url}")
                if desc:
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    output_parts.append(f"   {desc}")
                output_parts.append("")
            
            return "\n".join(output_parts)
        
        except Exception:
            return None

    def _search_fallback(self, query: str, count: int) -> str:
        """Fallback search using OpenClaw's built-in search tool."""
        try:
            # Import here to avoid circular imports
            import openclaw
            # Try to use OpenClaw's search capability
            # The search tool is available in the runtime
            from openclaw.tools import search as oc_search
            results = oc_search(query=query, count=count)
            
            if results and hasattr(results, 'results'):
                output_parts = [f"[Fallback] Search results for: {query}\n"]
                output_parts.append("=" * 50 + "\n")
                
                for i, item in enumerate(results.results[:count], 1):
                    title = getattr(item, 'title', 'No title')
                    item_url = getattr(item, 'url', 'No URL')
                    desc = getattr(item, 'content', getattr(item, 'description', ''))
                    
                    output_parts.append(f"{i}. {title}")
                    output_parts.append(f"   URL: {item_url}")
                    if desc:
                        if len(desc) > 200:
                            desc = desc[:200] + "..."
                        output_parts.append(f"   {desc}")
                    output_parts.append("")
                
                return "\n".join(output_parts)
        except Exception:
            pass
        
        return None

    def execute(self, query: str, count: int = 10, engines: Optional[str] = None) -> str:
        """Search the web with triple fallback: SearXNG → Tavily → web_fetch."""
        if not query or not query.strip():
            return "Error: Empty search query."
        
        count = min(max(1, count), 50)
        
        # 第一優先：SearXNG
        searxng_result = self._search_searxng(query, count, engines)
        if searxng_result:
            return searxng_result
        
        # 第二優先：Tavily API
        tavily_result = self._search_tavily(query, count)
        if tavily_result:
            return tavily_result
        
        # 第三優先：OpenClaw 內建 search (最後備援)
        try:
            import openclaw
            from openclaw import tools
            if hasattr(tools, 'search'):
                fallback_result = self._search_fallback(query, count)
                if fallback_result:
                    return fallback_result
        except Exception:
            pass
        
        return f"""Error: All search methods failed for query: "{query}"

Tried:
1. Local SearXNG (localhost:8888, localhost:8080) - returned no results or unavailable
2. Tavily API - not configured or failed (set TAVILY_API_KEY environment variable)
3. OpenClaw built-in search - not available in this environment

Note: SearXNG is running in Docker on port 8888. Some queries may return 0 results."""

    def _search_tavily(self, query: str, count: int) -> Optional[str]:
        """Try Tavily API if available."""
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return None
        
        try:
            import urllib.request
            import json
            
            data = json.dumps({
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": count
            }).encode("utf-8")
            
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
            
            if not result.get("results"):
                return None
            
            output_parts = [f"[Tavily] Search results for: {query}\n"]
            output_parts.append("=" * 50 + "\n")
            
            for i, item in enumerate(result["results"][:count], 1):
                title = item.get("title", "No title")
                item_url = item.get("url", "No URL")
                desc = item.get("content", "No description")
                
                output_parts.append(f"{i}. {title}")
                output_parts.append(f"   URL: {item_url}")
                if desc:
                    if len(desc) > 200:
                        desc = desc[:200] + "..."
                    output_parts.append(f"   {desc}")
                output_parts.append("")
            
            return "\n".join(output_parts)
        
        except Exception:
            return None


class WebFetchTool(Tool):
    """Fetch and extract readable content from web pages."""

    def __init__(self):
        self._user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch and extract readable content from a URL. Use this to read web pages, API responses, or other online content."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch"
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Maximum number of characters to return (default: 10000, max: 50000)"
                }
            },
            "required": ["url"]
        }

    def execute(self, url: str, max_chars: int = 10000) -> str:
        """Fetch content from a URL."""
        if not url or not url.strip():
            return "Error: Empty URL provided."
        
        # Basic URL validation
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            return f"Error: Invalid URL scheme. Must start with http:// or https://"
        
        max_chars = min(max(100, max_chars), 50000)  # Clamp between 100 and 50000
        
        try:
            headers = {
                "User-Agent": self._user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            req = urllib.request.Request(url, headers=headers, method="GET")
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                
                # Try to decode as text
                content_type = response.headers.get("Content-Type", "")
                
                if "text/html" in content_type or not content_type:
                    # Try UTF-8 first
                    try:
                        text = content.decode("utf-8")
                    except UnicodeDecodeError:
                        # Try other encodings
                        try:
                            text = content.decode("cp950")  # Traditional Chinese
                        except UnicodeDecodeError:
                            try:
                                text = content.decode("gb2312")  # Simplified Chinese
                            except UnicodeDecodeError:
                                text = content.decode("latin-1", errors="replace")
                    
                    # Basic HTML tag stripping
                    text = self._strip_html(text)
                    
                    # Clean up whitespace
                    text = self._clean_text(text)
                    
                    # Truncate if needed
                    if len(text) > max_chars:
                        text = text[:max_chars] + f"\n... (truncated, total {len(text)} chars)"
                    
                    return text
                else:
                    # Binary or unknown content type
                    return f"Error: Cannot fetch non-text content (Content-Type: {content_type})"
        
        except urllib.error.HTTPError as e:
            return f"Error: HTTP {e.code} - {e.reason}"
        except urllib.error.URLError as e:
            return f"Error: Could not fetch URL: {str(e)}"
        except Exception as e:
            return f"Error fetching URL: {str(e)}"

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        # Remove script and style elements
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        
        # Replace common HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        
        # Remove all HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        
        return text

    def _clean_text(self, text: str) -> str:
        """Clean up whitespace and normalize text."""
        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)
        
        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        
        # Remove leading/trailing blank lines
        text = text.strip()
        
        return text


class PythonREPLTool(Tool):
    """
    Execute Python code in a REPL-like environment.
    
    Uses subprocess to run Python code and captures output.
    Useful for quick calculations, data manipulation, etc.
    """

    def __init__(self):
        self._python_executable = sys.executable  # Use the same Python interpreter

    @property
    def name(self) -> str:
        return "python"

    @property
    def description(self) -> str:
        return """Execute Python code and return the output.
Use this for calculations, data manipulation, or running Python snippets.
The code is executed directly - no sandboxing."""

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (default: 30)"
                }
            },
            "required": ["code"]
        }

    def execute(self, code: str, timeout: int = 30) -> str:
        """Execute Python code."""
        if not code or not code.strip():
            return "Error: Empty Python code provided."
        
        timeout = min(max(1, timeout), 120)  # Clamp between 1 and 120 seconds
        
        try:
            # Execute Python code
            result = subprocess.run(
                [self._python_executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                errors="replace"
            )
            
            output_parts = []
            
            if result.stdout:
                output_parts.append(result.stdout.strip())
            
            if result.stderr:
                # Check if it's a warning or actual error
                stderr = result.stderr.strip()
                if result.returncode != 0:
                    return f"Error executing Python code:\n{stderr}"
                elif stderr:
                    # It's a warning, include it
                    output_parts.append(f"Warning:\n{stderr}")
            
            if not output_parts:
                if result.returncode == 0:
                    return "(Code executed successfully, no output)"
                else:
                    return f"Error: Code exited with code {result.returncode}"
            
            return "\n".join(output_parts)
        
        except subprocess.TimeoutExpired:
            return f"Error: Python code timed out after {timeout} seconds."
        except FileNotFoundError:
            return f"Error: Python interpreter not found: {self._python_executable}"
        except Exception as e:
            return f"Error executing Python: {str(e)}"


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self, include_default_tools: bool = True):
        self._tools: Dict[str, Tool] = {}

        if include_default_tools:
            # Register default tools
            self.register(BashTool())
            self.register(ReadTool())
            self.register(WriteTool())
            self.register(EditTool())
            self.register(WebSearchTool())
            self.register(WebFetchTool())
            self.register(PythonREPLTool())

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all(self) -> Dict[str, Tool]:
        """Get all registered tools."""
        return self._tools.copy()

    def get_tools_for_llm(self) -> list:
        """Get tools in OpenAI function calling format."""
        return [tool.to_openai_function() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs) -> str:
        """Execute a tool by name."""
        tool = self.get(name)
        if tool is None:
            return f"Error: Unknown tool '{name}'"
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return f"Error executing {name}: {str(e)}"


# For backward compatibility
BashToolOriginal = BashTool

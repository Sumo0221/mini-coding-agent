"""
platform_utils.py - Cross-Platform Command Translation Utilities

Handles Windows/Linux/Mac compatibility by translating Unix commands
to their Windows equivalents.
"""

import os
import platform
import re
from typing import Dict, Callable, Tuple, Optional
from functools import lru_cache


@lru_cache(maxsize=1)
def get_platform() -> str:
    """
    Get the current platform.
    
    Returns:
        'windows', 'linux', or 'darwin' (macOS)
    """
    system = platform.system().lower()
    if system == "windows" or os.name == "nt":
        return "windows"
    elif system == "darwin":
        return "darwin"
    else:
        return "linux"


def is_windows() -> bool:
    """Check if running on Windows."""
    return get_platform() == "windows"


def is_linux() -> bool:
    """Check if running on Linux."""
    return get_platform() == "linux"


def is_macos() -> bool:
    """Check if running on macOS."""
    return get_platform() == "darwin"


class CommandTranslator:
    """
    Translates Unix commands to Windows/PowerShell equivalents.
    
    Usage:
        translator = CommandTranslator()
        windows_cmd = translator.translate("ls -la")
        result = translator.execute_translated("ls -la")
    """
    
    def __init__(self):
        self.platform = get_platform()
        
        # Unix to Windows command mappings
        # Some are simple 1:1, others need special handling
        self._unix_to_windows: Dict[str, Callable[[list], str]] = {
            # File listing
            "ls": self._translate_ls,
            "ll": self._translate_ls,
            "la": self._translate_ls,
            "dir": self._passthrough,
            
            # File reading
            "cat": self._translate_cat,
            "type": self._passthrough,
            "head": self._translate_head,
            "tail": self._translate_tail,
            "more": self._passthrough,
            
            # File operations
            "rm": self._translate_rm,
            "del": self._passthrough,
            "rmdir": self._passthrough,
            "rd": self._passthrough,
            "cp": self._translate_cp,
            "copy": self._passthrough,
            "move": self._passthrough,
            "mv": self._translate_mv,
            "touch": self._translate_touch,
            
            # Directory operations
            "pwd": self._translate_pwd,
            "cd": self._passthrough,
            "chdir": self._passthrough,
            "mkdir": self._passthrough,
            "md": self._passthrough,
            
            # Search commands
            "grep": self._translate_grep,
            "find": self._translate_find,
            "findstr": self._passthrough,
            "which": self._translate_which,
            "where": self._passthrough,
            
            # Text processing
            "wc": self._translate_wc,
            "sort": self._passthrough,
            "uniq": self._passthrough,
            "cut": self._translate_cut,
            "awk": self._translate_awk,
            "sed": self._translate_sed,
            
            # System commands
            "clear": self._translate_clear,
            "cls": self._passthrough,
            "echo": self._passthrough,
            "kill": self._passthrough,
            "ps": self._translate_ps,
            "top": self._translate_top,
            "history": self._translate_history,
            
            # Git commands (usually available on Windows via Git Bash)
            "git": self._passthrough,
            
            # Python commands
            "python": self._passthrough,
            "python3": self._passthrough,
            "pip": self._passthrough,
            "pip3": self._passthrough,
            
            # Archive commands
            "tar": self._translate_tar,
            "unzip": self._passthrough,
            "zip": self._passthrough,
        }
    
    def _passthrough(self, cmd: str, args: list) -> str:
        """Pass through command as-is."""
        if args:
            return f"{cmd} {' '.join(args)}"
        return cmd
    
    def _translate_ls(self, args: list) -> str:
        """Translate ls to dir."""
        # Common ls flags that dir supports
        flags = []
        files = []
        for arg in args:
            if arg.startswith("-"):
                flags.append(arg)
            else:
                files.append(arg)
        
        # Build dir command - /b = bare format, /a = show hidden
        cmd_parts = ["dir"]
        if "-a" in flags or "-l" in flags or "--all" in flags:
            cmd_parts.append("/a")
        if "/b" not in " ".join(flags):
            cmd_parts.append("/b")  # Bare format (like ls)
        
        cmd_parts.extend(files)
        return " ".join(cmd_parts)
    
    def _translate_cat(self, args: list) -> str:
        """Translate cat to type."""
        if not args:
            return "type"
        return "type " + " ".join(args)
    
    def _translate_head(self, args: list) -> str:
        """Translate head -n N file to PowerShell equivalent."""
        n = 10  # default
        files = []
        for i, arg in enumerate(args):
            if arg in ["-n", "--lines"]:
                if i + 1 < len(args):
                    try:
                        n = int(args[i + 1])
                    except ValueError:
                        pass
            elif arg.isdigit():
                n = int(arg)
            elif not arg.startswith("-"):
                files.append(arg)
        
        if not files:
            return f"Get-Content -Head {n}"
        return f"Get-Content -Head {n} {files[0]}"
    
    def _translate_tail(self, args: list) -> str:
        """Translate tail -n N file to PowerShell equivalent."""
        n = 10  # default
        files = []
        for i, arg in enumerate(args):
            if arg in ["-n", "--lines"]:
                if i + 1 < len(args):
                    try:
                        n = int(args[i + 1])
                    except ValueError:
                        pass
            elif arg.isdigit():
                n = int(arg)
            elif not arg.startswith("-"):
                files.append(arg)
        
        if not files:
            return f"Get-Content -Tail {n}"
        return f"Get-Content -Tail {n} {files[0]}"
    
    def _translate_rm(self, args: list) -> str:
        """Translate rm to del."""
        if not args:
            return "del"
        
        cmd_parts = ["del"]
        for arg in args:
            if not arg.startswith("-"):
                cmd_parts.append(arg)
        return " ".join(cmd_parts)
    
    def _translate_cp(self, args: list) -> str:
        """Translate cp to copy."""
        if not args:
            return "copy"
        return "copy " + " ".join(args)
    
    def _translate_mv(self, args: list) -> str:
        """Translate mv to move."""
        if not args:
            return "move"
        return "move " + " ".join(args)
    
    def _translate_touch(self, args: list) -> str:
        """Translate touch to create file."""
        if not args:
            return "type nul"
        # For Windows, we can use: type nul > filename
        return f"type nul > {args[0]}"
    
    def _translate_pwd(self, args: list) -> str:
        """Translate pwd to cd (shows current directory)."""
        return "cd"
    
    def _translate_grep(self, args: list) -> str:
        """Translate grep to findstr."""
        if not args:
            return "findstr"
        
        cmd_parts = ["findstr"]
        pattern = None
        files = []
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ["-i", "/i", "--ignore-case"]:
                cmd_parts.append("/i")
            elif arg in ["-v", "/v", "--invert-match"]:
                cmd_parts.append("/v")
            elif arg in ["-n", "--line-number"]:
                cmd_parts.append("/n")  # findstr uses /n for line numbers
            elif arg in ["-r", "-R", "/s", "--recursive"]:
                pass  # findstr /s is similar
            elif arg.startswith("-"):
                pass  # Skip other flags
            elif pattern is None:
                # First non-flag is the pattern
                pattern = arg
                # findstr uses /c:"pattern" for patterns with spaces
                if " " in arg:
                    cmd_parts.append(f'/c:"{arg}"')
                else:
                    cmd_parts.append(arg)
            else:
                # Everything else is a file
                files.append(arg)
            i += 1
        
        if files:
            # findstr can search multiple files
            cmd_parts.append(" ".join(files))
        
        return " ".join(cmd_parts)
    
    def _translate_find(self, args: list) -> str:
        """Translate find to PowerShell Get-ChildItem -Recurse."""
        if not args:
            return "Get-ChildItem"
        
        name_pattern = None
        search_path = "."
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-name" and i + 1 < len(args):
                name_pattern = args[i + 1]
            elif arg == "-type" and i + 1 < len(args):
                # f = files, d = directories - translate appropriately
                if args[i + 1] == "f":
                    pass  # default in PowerShell
                elif args[i + 1] == "d":
                    cmd_parts.append("/ad")
            elif not arg.startswith("-"):
                search_path = arg
            i += 1
        
        if name_pattern:
            # Convert * wildcard to PowerShell format
            ps_pattern = name_pattern.replace("*", "*")
            return f'Get-ChildItem -Path "{search_path}" -Recurse -Filter "{ps_pattern}"'
        return f'Get-ChildItem -Path "{search_path}" -Recurse'
    
    def _translate_which(self, args: list) -> str:
        """Translate which to where (Windows)."""
        if not args:
            return "where"
        return "where " + " ".join(args)
    
    def _translate_wc(self, args: list) -> str:
        """Translate wc to PowerShell line count."""
        file = None
        for arg in args:
            if not arg.startswith("-"):
                file = arg
        
        if file:
            return f'(Get-Content "{file}").Length'
        return "(Get-Content).Length"
    
    def _translate_cut(self, args: list) -> str:
        """Translate cut to PowerShell equivalent."""
        # This is complex - simplified version
        return "$input | ForEach-Object { $_.Substring(0, [Math]::Min(100, $_.Length)) }"
    
    def _translate_awk(self, args: list) -> str:
        """Translate awk to PowerShell equivalent."""
        # Very simplified - full awk translation is complex
        return "$input | ForEach-Object { $_ }"
    
    def _translate_sed(self, args: list) -> str:
        """Translate sed to PowerShell equivalent."""
        # Simplified sed translation
        return "$input"
    
    def _translate_clear(self, args: list) -> str:
        """Translate clear to cls."""
        return "cls"
    
    def _translate_ps(self, args: list) -> str:
        """Translate ps to Get-Process."""
        if not args:
            return "Get-Process"
        
        # ps aux -> Get-Process | Format-Table
        if "-a" in args or "aux" in args:
            return "Get-Process | Format-Table"
        
        # ps | Select-Object Name, Id, CPU
        return "Get-Process | Select-Object Name, Id, CPU"
    
    def _translate_top(self, args: list) -> str:
        """Translate top to Get-Process sorted by CPU."""
        return "Get-Process | Sort-Object CPU -Descending | Select-Object -First 20"
    
    def _translate_history(self, args: list) -> str:
        """Translate history to Get-History."""
        return "Get-History"
    
    def _translate_tar(self, args: list) -> str:
        """Translate tar to 7z or tar if available."""
        # Check if tar is available (Git Bash, WSL, etc.)
        # For pure Windows, suggest 7-Zip
        return "7z"
    
    def translate(self, command: str) -> Tuple[str, bool]:
        """
        Translate a Unix command string to Windows equivalent.
        
        Args:
            command: The Unix command string (e.g., "ls -la", "cat file.txt")
            
        Returns:
            Tuple of (translated_command, was_translated)
            was_translated is True if the command was modified for Windows.
        """
        if not command.strip():
            return command, False
        
        # If not on Windows, return command as-is
        if self.platform != "windows":
            return command, False
        
        # Split command into parts
        parts = command.strip().split()
        if not parts:
            return command, False
        
        cmd = parts[0]
        args = parts[1:]
        
        # Check if this command needs translation
        if cmd in self._unix_to_windows:
            translator_func = self._unix_to_windows[cmd]
            try:
                # For _passthrough, pass (cmd, args) tuple
                if translator_func == self._passthrough:
                    translated = translator_func(cmd, args)
                else:
                    translated = translator_func(args)
                return translated, translated != command
            except Exception:
                # If translation fails, return original
                return command, False
        
        # Check for piped commands
        if "|" in command:
            # Try to translate each part of the pipe
            translated_parts = []
            for part in command.split("|"):
                part = part.strip()
                t_part, _ = self.translate(part)
                translated_parts.append(t_part)
            return " | ".join(translated_parts), True
        
        # Command not found in translation table - pass through
        return command, False
    
    def execute_translated(self, command: str) -> str:
        """
        Execute a command with automatic translation.
        
        Returns tuple of (output, was_translated).
        """
        translated, was_translated = self.translate(command)
        return translated, was_translated


# Global translator instance
_translator: Optional[CommandTranslator] = None


def get_translator() -> CommandTranslator:
    """Get the global CommandTranslator instance."""
    global _translator
    if _translator is None:
        _translator = CommandTranslator()
    return _translator


def translate_command(cmd: str) -> Tuple[str, bool]:
    """
    Convenience function to translate a command.
    
    Returns Tuple of (translated_command, was_translated).
    """
    return get_translator().translate(cmd)


def safe_encode_for_output(text: str, encoding: str = "utf-8") -> str:
    """
    Safely encode text for output, handling encoding errors.
    
    For Windows Traditional Chinese (cp950) environments,
    this tries to encode and falls back gracefully.
    """
    if is_windows():
        # Try UTF-8 first, then fallback to cp950 for Chinese
        try:
            return text.encode(encoding).decode(encoding)
        except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
            try:
                # Fallback to cp950 for Traditional Chinese on Windows
                return text.encode("cp950", errors="replace").decode("cp950", errors="replace")
            except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
                # Last resort: ASCII with replacement
                return text.encode("ascii", errors="replace").decode("ascii", errors="replace")
    return text


def get_safe_encoding() -> str:
    """
    Get the safe encoding for the current platform.
    """
    if is_windows():
        # Check for Traditional Chinese locale
        import locale
        try:
            lang = locale.getdefaultlocale()[0]
            if lang and lang.startswith("zh"):
                return "cp950"  # Traditional Chinese
        except Exception:
            pass
        return "utf-8"
    return "utf-8"

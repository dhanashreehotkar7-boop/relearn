"""
Re:Learn - C Code Runner and Windows GCC Error Diagnostics Parser
"""

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

# Regex specifically anchored to avoid mistaking Windows drive letters (e.g. C:) for line numbers
# Matches "C:\path\file.c:7:5: error: message" or "file.c:7:5: warning: message"
GCC_DIAGNOSTIC_REGEX = re.compile(
    r"^(?:[A-Za-z]:)?[^:\r\n]+:(\d+):(\d+):\s*(error|warning|note):\s*(.*?)$",
    re.MULTILINE
)

@dataclass
class GCCDiagnostic:
    line: int
    column: int
    kind: str  # "error", "warning", "note"
    message: str
    friendly_explanation: str
    highlight_lines: Optional[List[int]] = None

@dataclass
class CodeRunResult:
    success: bool
    stage: str  # "compile", "execute", or "timeout"
    stdout: str
    stderr: str
    return_code: Optional[int]
    diagnostics: List[GCCDiagnostic]
    raw_error: Optional[str] = None

def get_friendly_explanation(message: str) -> str:
    """
    Finds a friendly explanation based on keyword lookups in gcc diagnostics.
    Uses resilient keyword checks rather than full sentence matches.
    """
    msg = message.lower()

    # Semicolon missing (e.g. "expected ';'", "expected ',' or ';'", "expected ';' before")
    if "expected" in msg and (";" in msg or "semicolon" in msg):
        return "You might have forgotten a semicolon (;) at the end of this statement or on the line directly above."

    # Undeclared variable/function
    if "undeclared" in msg or "has not been declared" in msg:
        return "This variable or identifier is not declared. Check for typos or declare it with its type (e.g. int, char) before using it."

    # Implicit declaration of function (missing header like stdio.h)
    if "implicit declaration" in msg:
        return "You called a function that was not declared. Did you forget an #include directive (e.g. #include <stdio.h> or <stdlib.h>)?"

    # Format specifier mismatch in printf/scanf
    if "format" in msg and ("argument" in msg or "type" in msg or "%" in msg or "expects" in msg):
        return "The format specifier in printf/scanf (e.g. %d, %s, %f) does not match the data type of the argument provided."

    # Assignment inside condition (= vs ==)
    if "assignment" in msg and ("truth value" in msg or "parentheses" in msg or "conditional" in msg):
        return "You used a single '=' (assignment) inside a conditional check. Did you mean '==' (equality comparison)?"

    # Missing return in non-void function
    if "non-void" in msg and "reaches end" in msg:
        return "This function is expected to return a value, but execution reached the end without a 'return' statement."

    # Array assignment
    if "array type" in msg and ("assignment" in msg or "incompatible" in msg):
        return "In C, you cannot assign to an array directly using '='. Use strcpy() or assign values element-by-element."

    # Subscript on non-array
    if "subscripted value" in msg and ("neither array nor pointer" in msg or "pointer" in msg):
        return "You used square brackets [ ] on a variable that is not an array or a pointer."

    # Function argument count
    if "too few arguments" in msg:
        return "This function was called with fewer arguments than its definition requires."
    if "too many arguments" in msg:
        return "This function was called with more arguments than its definition accepts."

    # Conflicting types
    if "conflicting types" in msg:
        return "The declaration or signature of this function/variable conflicts with a previous declaration or prototype."

    # Division by zero
    if "division by zero" in msg:
        return "Dividing by zero causes a runtime exception or undefined behavior."

    # Unused variable
    if "unused variable" in msg or ("unused" in msg and "variable" in msg):
        return "This variable was declared but never read or written elsewhere in the function."

    # Array out of bounds warning
    if "array subscript" in msg and ("bounds" in msg or "above" in msg or "below" in msg):
        return "You are attempting to access an index outside the declared size of this array."

    return "C compiler diagnostic. Review the line and column indicated in your code."

def sanitize_gcc_stderr(raw_stderr: str) -> str:
    """
    Cleans GCC compiler output for students:
    - Strips long temporary directory paths (e.g. C:\\Users\\...\\program.c: -> solution.c:)
    - Filters out internal test harness warnings (e.g. freeList, createNode, buildList).
    """
    if not raw_stderr:
        return ""

    lines = raw_stderr.splitlines()
    cleaned = []

    for line in lines:
        # Filter internal harness functions
        if any(h in line for h in ("freeList", "createNode", "buildList", "HARNESS DRIVER", "__main")):
            continue
        # Replace messy temp paths with solution.c
        subbed = re.sub(r'^[A-Za-z]:[\\/][^\n:]+[\\/](?:program|solution)\.c:', 'solution.c:', line)
        cleaned.append(subbed)

    return "\n".join(cleaned)

def parse_gcc_errors(stderr_text: str) -> List[GCCDiagnostic]:
    """
    Parses Windows-style GCC error lines.
    Handles drive letters without mistaking colons for line numbers.
    """
    diagnostics: List[GCCDiagnostic] = []
    if not stderr_text:
        return diagnostics

    for match in GCC_DIAGNOSTIC_REGEX.finditer(stderr_text):
        line_str, col_str, kind, msg = match.groups()
        try:
            line_num = int(line_str)
            col_num = int(col_str)
        except ValueError:
            continue

        clean_msg = msg.strip()
        # Skip harness internals
        if any(h in clean_msg for h in ("freeList", "createNode", "buildList")):
            continue

        explanation = get_friendly_explanation(clean_msg)
        
        # Polish: If missing semicolon before a token, highlight reported line and the line above
        highlight_lines = [line_num]
        if "expected" in clean_msg.lower() and (";" in clean_msg or "semicolon" in clean_msg):
            highlight_lines = [line_num, max(1, line_num - 1)]

        diagnostics.append(
            GCCDiagnostic(
                line=line_num,
                column=col_num,
                kind=kind.lower(),
                message=clean_msg,
                friendly_explanation=explanation,
                highlight_lines=highlight_lines
            )
        )

    return diagnostics

def compile_c_source(
    code: str,
    tmp_path: Path,
    timeout_compile: float = 10.0
) -> Tuple[bool, Optional[Path], str, List[GCCDiagnostic]]:
    """
    Compiles C source code inside tmp_path using MinGW gcc.
    Returns (success, exe_path_if_successful, stderr_text, diagnostics).
    """
    source_file = tmp_path / "program.c"
    exe_file = tmp_path / "program.exe"

    source_file.write_text(code, encoding="utf-8")

    compile_cmd = [
        "gcc",
        "-std=c99",
        "-Wall",
        "-o",
        str(exe_file.resolve()),
        str(source_file.resolve())
    ]

    try:
        compile_proc = subprocess.run(
            compile_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_compile,
            cwd=str(tmp_path)
        )
    except subprocess.TimeoutExpired:
        return False, None, "Compilation timed out (>10s).", []
    except FileNotFoundError:
        return False, None, "gcc executable not found on system PATH. Please ensure MinGW GCC is installed.", []

    sanitized_stderr = sanitize_gcc_stderr(compile_proc.stderr)

    if compile_proc.returncode != 0:
        diagnostics = parse_gcc_errors(compile_proc.stderr)
        return False, None, sanitized_stderr, diagnostics

    return True, exe_file, sanitized_stderr, []

def run_c_executable(
    exe_file: Path,
    stdin_input: str,
    tmp_path: Path,
    timeout_exec: float = 2.0
) -> CodeRunResult:
    """
    Executes compiled C program binary by its full absolute path.
    """
    try:
        run_proc = subprocess.run(
            [str(exe_file.resolve())],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=timeout_exec,
            cwd=str(tmp_path)
        )
        return CodeRunResult(
            success=(run_proc.returncode == 0),
            stage="execute",
            stdout=run_proc.stdout,
            stderr=run_proc.stderr,
            return_code=run_proc.returncode,
            diagnostics=[]
        )
    except subprocess.TimeoutExpired:
        return CodeRunResult(
            success=False,
            stage="timeout",
            stdout="",
            stderr="Execution timed out (>2.0s). Check for infinite loops.",
            return_code=-1,
            diagnostics=[],
            raw_error="Execution timed out."
        )
    except Exception as e:
        return CodeRunResult(
            success=False,
            stage="execute",
            stdout="",
            stderr=str(e),
            return_code=-1,
            diagnostics=[],
            raw_error=str(e)
        )

def compile_and_run(
    code: str,
    timeout_compile: float = 10.0,
    timeout_exec: float = 2.0,
    stdin_input: str = ""
) -> CodeRunResult:
    """Convenience wrapper: Compiles and executes C code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ok, exe_file, stderr, diags = compile_c_source(code, tmp_path, timeout_compile)
        if not ok or exe_file is None:
            return CodeRunResult(
                success=False,
                stage="compile",
                stdout="",
                stderr=stderr,
                return_code=-1,
                diagnostics=diags,
                raw_error=stderr
            )
        return run_c_executable(exe_file, stdin_input, tmp_path, timeout_exec)

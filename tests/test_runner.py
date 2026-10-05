"""
Unit and Integration Tests for Re:Learn C Code Runner and GCC Diagnostics Parser
"""

import unittest
from app.runner import (
    parse_gcc_errors,
    get_friendly_explanation,
    compile_and_run,
    GCCDiagnostic
)

class TestGCCParser(unittest.TestCase):
    def test_windows_drive_letter_path_parsing(self):
        """Ensure Windows drive letters (e.g. C:, D:) are never mistaken for line numbers."""
        sample_stderr = (
            r"C:\Users\Dhanashree07\AppData\Local\Temp\tmpxyz123\program.c:7:5: error: expected ';' before 'return'" + "\n"
            r"C:\Users\Dhanashree07\AppData\Local\Temp\tmpxyz123\program.c:12:10: error: 'count' undeclared (first use in this function)" + "\n"
            r"D:\projects\c_learning\arrays.c:20:9: warning: implicit declaration of function 'pritnf' [-Wimplicit-function-declaration]"
        )

        diagnostics = parse_gcc_errors(sample_stderr)
        self.assertEqual(len(diagnostics), 3)

        # Diagnostic 1
        self.assertEqual(diagnostics[0].line, 7)
        self.assertEqual(diagnostics[0].column, 5)
        self.assertEqual(diagnostics[0].kind, "error")
        self.assertIn("semicolon", diagnostics[0].friendly_explanation.lower())

        # Diagnostic 2
        self.assertEqual(diagnostics[1].line, 12)
        self.assertEqual(diagnostics[1].column, 10)
        self.assertEqual(diagnostics[1].kind, "error")
        self.assertIn("declared", diagnostics[1].friendly_explanation.lower())

        # Diagnostic 3
        self.assertEqual(diagnostics[2].line, 20)
        self.assertEqual(diagnostics[2].column, 9)
        self.assertEqual(diagnostics[2].kind, "warning")
        self.assertIn("implicit declaration", diagnostics[2].message.lower())
        self.assertIn("include", diagnostics[2].friendly_explanation.lower())

    def test_windows_path_with_spaces_and_special_chars(self):
        """Test parsing errors when paths contain spaces or parentheses."""
        sample_stderr = (
            r"C:\Program Files (x86)\Code Projects\solution.c:15:3: error: assignment to expression with array type" + "\n"
            r"E:\c\nested dir\file.c:42:1: warning: control reaches end of non-void function [-Wreturn-type]"
        )
        diagnostics = parse_gcc_errors(sample_stderr)
        self.assertEqual(len(diagnostics), 2)
        self.assertEqual(diagnostics[0].line, 15)
        self.assertEqual(diagnostics[0].column, 3)
        self.assertEqual(diagnostics[0].kind, "error")
        self.assertIn("array", diagnostics[0].friendly_explanation.lower())

        self.assertEqual(diagnostics[1].line, 42)
        self.assertEqual(diagnostics[1].column, 1)
        self.assertEqual(diagnostics[1].kind, "warning")
        self.assertIn("return", diagnostics[1].friendly_explanation.lower())

    def test_keyword_resilient_friendly_explanations(self):
        """Test that variations across GCC versions match friendly explanations based on keywords."""
        test_cases = [
            ("expected ';' before '}' token", "semicolon"),
            ("expected ',' or ';' before 'return'", "semicolon"),
            ("error: expected ';'", "semicolon"),
            ("'total' undeclared (first use in this function)", "declared"),
            ("implicit declaration of function 'malloc'", "include"),
            ("format '%d' expects argument of type 'int', but argument 2 has type 'double'", "format"),
            ("suggest parentheses around assignment used as truth value", "=="),
            ("assignment to expression with array type", "array"),
            ("subscripted value is neither array nor pointer nor vector", "array"),
            ("too few arguments to function 'sum'", "fewer arguments"),
            ("too many arguments to function 'calc'", "more arguments"),
            ("control reaches end of non-void function [-Wreturn-type]", "return")
        ]

        for gcc_msg, keyword_expected in test_cases:
            explanation = get_friendly_explanation(gcc_msg)
            self.assertIn(keyword_expected, explanation.lower(), f"Failed matching explanation for: {gcc_msg}")

class TestCodeExecution(unittest.TestCase):
    def test_successful_c_compilation_and_execution(self):
        """Test compiling and running real C code using Windows MinGW gcc."""
        code = """#include <stdio.h>

int main(void) {
    int arr[3] = {10, 20, 30};
    printf("Result: %d\\n", arr[1]);
    return 0;
}"""
        result = compile_and_run(code)
        self.assertTrue(result.success)
        self.assertEqual(result.stage, "execute")
        self.assertEqual(result.stdout.strip(), "Result: 20")
        self.assertEqual(result.return_code, 0)
        self.assertEqual(len(result.diagnostics), 0)

    def test_real_gcc_error_diagnostics(self):
        """Test compiling invalid C code to ensure real MinGW gcc error output is parsed accurately."""
        bad_code = """#include <stdio.h>

int main(void) {
    int x = 42
    return 0;
}"""
        result = compile_and_run(bad_code)
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "compile")
        self.assertNotEqual(result.return_code, 0)
        self.assertTrue(len(result.diagnostics) >= 1)
        
        # Verify first diagnostic points to line 4 (missing semicolon before return)
        first_diag = result.diagnostics[0]
        self.assertEqual(first_diag.kind, "error")
        self.assertIn("semicolon", first_diag.friendly_explanation.lower())

    def test_timeout_handling_infinite_loop(self):
        """Test that infinite loops are halted safely with a timeout."""
        infinite_loop_code = """#include <stdio.h>

int main(void) {
    while(1) {
        // infinite loop
    }
    return 0;
}"""
        result = compile_and_run(infinite_loop_code, timeout_exec=1.5)
        self.assertFalse(result.success)
        self.assertEqual(result.stage, "timeout")
        self.assertIn("timed out", result.stderr.lower())

if __name__ == "__main__":
    unittest.main()

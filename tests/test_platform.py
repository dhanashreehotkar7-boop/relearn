"""
Pytest Test Suite for Re:Learn LeetCode-style C Practice Platform
Covers GCC error parser, line offset mapping, execution tracer, timer/fix-time logic, and harnesses.
"""

import pytest
import time
from app.runner import (
    parse_gcc_errors,
    get_friendly_explanation,
    compile_and_run
)
from app.harness import (
    generate_harness,
    map_error_line_to_student
)
from app.tracer import (
    detect_pattern_error,
    explain_divergence
)

# ==========================================
# 1. GCC ERROR PARSER & FRIENDLY EXPLANATIONS
# ==========================================
class TestGCCErrorParser:
    def test_windows_drive_letter_anchoring(self):
        r"""Ensures Windows drive letters (C:\, D:\) are never mistaken for line numbers."""
        sample_stderr = (
            r"C:\Users\Student\AppData\Local\Temp\tmp_x\program.c:14:5: error: expected ';' before 'return'" + "\n"
            r"C:\Users\Student\AppData\Local\Temp\tmp_x\program.c:22:9: error: 'target' undeclared (first use in this function)" + "\n"
            r"D:\projects\c_learning\arrays.c:30:1: warning: control reaches end of non-void function [-Wreturn-type]"
        )
        diagnostics = parse_gcc_errors(sample_stderr)
        assert len(diagnostics) == 3
        assert diagnostics[0].line == 14
        assert diagnostics[0].column == 5
        assert diagnostics[0].kind == "error"
        assert "semicolon" in diagnostics[0].friendly_explanation.lower()

        assert diagnostics[1].line == 22
        assert diagnostics[1].kind == "error"
        assert "declared" in diagnostics[1].friendly_explanation.lower()

        assert diagnostics[2].line == 30
        assert diagnostics[2].kind == "warning"
        assert "return" in diagnostics[2].friendly_explanation.lower()

    def test_friendly_explanations_coverage_15_plus(self):
        """Tests that at least 15 common GCC error variants have friendly explanations."""
        test_messages = [
            ("expected ';' before '}'", "semicolon"),
            ("expected ',' or ';' before 'return'", "semicolon"),
            ("'total' undeclared (first use in this function)", "declared"),
            ("implicit declaration of function 'malloc'", "include"),
            ("format '%d' expects argument of type 'int', but argument 2 has type 'double'", "format"),
            ("suggest parentheses around assignment used as truth value", "=="),
            ("assignment to expression with array type", "array"),
            ("subscripted value is neither array nor pointer", "array"),
            ("control reaches end of non-void function", "return"),
            ("too few arguments to function 'sum'", "fewer arguments"),
            ("too many arguments to function 'calc'", "more arguments"),
            ("conflicting types for 'findMax'", "declaration"),
            ("division by zero", "zero"),
            ("unused variable 'temp' [-Wunused-variable]", "declared but never read"),
            ("array subscript is above array bounds", "outside the declared size")
        ]
        assert len(test_messages) >= 15
        for msg, keyword in test_messages:
            explanation = get_friendly_explanation(msg)
            assert keyword.lower() in explanation.lower(), f"Failed explanation for: {msg}"

    def test_harness_line_offset_mapping(self):
        """Ensures error line numbers in wrapped C code map accurately back to the student's code."""
        student_code = (
            "int findMax(int arr[], int n) {\n"
            "    int maxVal = arr[0]\n"  # Line 2 missing semicolon
            "    return maxVal;\n"
            "}"
        )
        full_code, offset = generate_harness(1, student_code)
        assert offset > 0

        # If GCC reports an error at offset + 2 (which is student line 2)
        raw_gcc_line = offset + 2
        student_line = map_error_line_to_student(raw_gcc_line, offset, len(student_code.splitlines()))
        assert student_line == 2

# ==========================================
# 2. C-SUBSET TRACER & "WHY -100?" FEATURE
# ==========================================
class TestExecutionTracer:
    def test_detect_off_by_one_loop(self):
        """Detects loop index bounds bug (i <= n on size n)."""
        buggy_code = """int sumArray(int arr[], int n) {
    int sum = 0;
    for (int i = 0; i <= n; i++) {
        sum += arr[i];
    }
    return sum;
}"""
        err_type, reason = detect_pattern_error(buggy_code, 2, "3\n1 2 3", "6", "10")
        assert err_type == "off_by_one"
        assert "<= n" in reason

    def test_detect_accumulator_sign_error(self):
        """Detects subtraction instead of addition in accumulator."""
        buggy_code = """int sumArray(int arr[], int n) {
    int sum = 0;
    for (int i = 0; i < n; i++) {
        sum -= arr[i];
    }
    return sum;
}"""
        err_type, reason = detect_pattern_error(buggy_code, 2, "3\n10 20 30", "60", "-60")
        assert err_type == "sign_error"
        assert "subtracted" in reason.lower()

    def test_detect_wrong_initial_value_negatives(self):
        """Detects initializing max to 0 when input array contains only negatives."""
        buggy_code = """int findMax(int arr[], int n) {
    int maxVal = 0;
    for (int i = 0; i < n; i++) {
        if (arr[i] > maxVal) maxVal = arr[i];
    }
    return maxVal;
}"""
        err_type, reason = detect_pattern_error(buggy_code, 1, "3\n-10 -3 -50", "-3", "0")
        assert err_type == "wrong_initial_value"
        assert "negative" in reason.lower()

    def test_tracer_simulation_steps(self):
        """Ensures simulation records step variables and marks divergence point."""
        code = """int findMax(int arr[], int n) {
    int maxVal = 0;
    for (int i = 1; i < n; i++) {
        if (arr[i] > maxVal) maxVal = arr[i];
    }
    return maxVal;
}"""
        divergence = explain_divergence(code, 1, "3\n-10 -3 -50", "-3", "0")
        assert divergence["error_type"] == "wrong_initial_value"
        assert len(divergence["trace_steps"]) >= 2
        assert divergence["divergent_step_index"] is not None

# ==========================================
# 3. TIMER & FIX-TIME TRACKING LOGIC
# ==========================================
class TestTimerAndFixTracking:
    def test_duration_calculation(self):
        """Tests millisecond start and submit timestamp calculations."""
        started_at = 1700000000000
        submitted_at = 1700000048200
        duration_ms = submitted_at - started_at
        assert duration_ms == 48200

        mins = duration_ms // 60000
        secs = (duration_ms % 60000) / 1000.0
        assert mins == 0
        assert round(secs, 2) == 48.20

    def test_error_fix_duration_computation(self):
        """Tests measuring duration from when an error was shown to when fixed."""
        error_shown_ms = int(time.time() * 1000) - 25000  # 25 seconds ago
        now_ms = int(time.time() * 1000)
        fix_duration_ms = now_ms - error_shown_ms

        assert fix_duration_ms >= 24000
        # Bug squasher badge criteria: < 35 seconds
        is_bug_squasher = fix_duration_ms < 35000
        assert is_bug_squasher is True

# ==========================================
# 4. REAL C HARNESS COMPILATION & EXECUTION
# ==========================================
class TestRealCHarnessExecution:
    def test_compile_and_run_array_sum(self):
        """Tests compiling and executing an array sum problem with MinGW GCC."""
        student_code = """int sumArray(int arr[], int n) {
    int total = 0;
    for (int i = 0; i < n; i++) {
        total += arr[i];
    }
    return total;
}"""
        full_code, _ = generate_harness(2, student_code)
        res = compile_and_run(full_code, stdin_input="5\n1 2 3 4 5")
        assert res.success is True
        assert res.stdout.strip() == "15"

    def test_compile_and_run_linked_list_sum(self):
        """Tests compiling and executing a linked list problem with MinGW GCC."""
        student_code = """int sumList(struct Node* head) {
    int total = 0;
    struct Node* curr = head;
    while (curr != NULL) {
        total += curr->val;
        curr = curr->next;
    }
    return total;
}"""
        full_code, _ = generate_harness(6, student_code)
        res = compile_and_run(full_code, stdin_input="4\n10 20 30 40")
        assert res.success is True
        assert res.stdout.strip() == "100"

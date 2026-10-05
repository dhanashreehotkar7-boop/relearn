"""
Re:Learn - Comprehensive C Code Execution Tracer & Animation Generator
Generates rich step-by-step animation data for all 10 problems:
- Arrays: pointer positions (i, left, right), cell highlights, swaps, value graphs
- Linked Lists: node boxes, pointer tags (prev, curr, next), pointer reversal, NULL
- Divergence detection: side-by-side comparison with model solution
"""

import re
from typing import Dict, List, Any, Optional, Tuple

def parse_input_for_problem(problem_id: int, input_str: str) -> Dict[str, Any]:
    """Parses standard test case input format for problems."""
    lines = input_str.strip().split("\n")
    if not lines or not lines[0].strip():
        return {"n": 0, "arr": [], "target": None}

    first_line_parts = [int(x) for x in lines[0].strip().split() if x.lstrip('-').isdigit()]
    n = first_line_parts[0] if first_line_parts else 0
    target = first_line_parts[1] if len(first_line_parts) > 1 else None

    arr = []
    if len(lines) > 1 and lines[1].strip():
        arr = [int(x) for x in lines[1].strip().split() if x.lstrip('-').isdigit()]
    elif len(first_line_parts) > 1 and target is None:
        arr = first_line_parts[1:]

    return {"n": n, "arr": arr, "target": target}

def trace_problem(problem_id: int, code: str, input_str: str, is_model_solution: bool = False) -> Dict[str, Any]:
    """
    Generates step-by-step animation frames for problem execution.
    Handles all 10 problems with array state, pointer slides, linked list arrows,
    and value histories for live graphing.
    """
    data = parse_input_for_problem(problem_id, input_str)
    n = data["n"]
    arr = list(data["arr"])
    target = data["target"]

    steps: List[Dict[str, Any]] = []
    code_clean = re.sub(r'//.*', '', code)

    # =========================================================================
    # Problem 1: Find Maximum in Array
    # =========================================================================
    if problem_id == 1:
        if not arr:
            arr = [10, 20, 30]
            n = len(arr)

        # Detect if student initialized to 0
        starts_at_zero = bool(re.search(r'(?:int\s+)?(?:max|maxVal)\s*=\s*0\s*;', code_clean)) and not is_model_solution
        starts_loop_at_zero = bool(re.search(r'for\s*\(\s*(?:int\s+)?i\s*=\s*0\s*;', code_clean))

        max_val = 0 if starts_at_zero else arr[0]
        val_history = [max_val]

        steps.append({
            "step": 1,
            "line": 2,
            "caption": f"Initialize maxVal = {'0 (Warning: fails if array has negative numbers)' if starts_at_zero else f'arr[0] ({arr[0]})'}",
            "variables": {"n": n, "maxVal": max_val},
            "value_history": {"maxVal": list(val_history)},
            "pointers": {"max": 0 if not starts_at_zero else None},
            "array_data": [{"val": v, "idx": i, "highlight": "active" if i == 0 and not starts_at_zero else "none"} for i, v in enumerate(arr)],
            "note": "Initial state before loop"
        })

        start_i = 0 if starts_loop_at_zero else 1
        for i in range(start_i, len(arr)):
            curr_val = arr[i]
            is_greater = curr_val > max_val
            
            # Step A: Comparison
            steps.append({
                "step": len(steps) + 1,
                "line": 4,
                "caption": f"Index i = {i}: Comparing arr[{i}] ({curr_val}) with current maxVal ({max_val})",
                "variables": {"i": i, "arr[i]": curr_val, "maxVal": max_val, "n": n},
                "value_history": {"maxVal": list(val_history)},
                "pointers": {"i": i},
                "array_data": [{"val": v, "idx": idx, "highlight": "comparing" if idx == i else ("active" if v == max_val else "none")} for idx, v in enumerate(arr)],
                "note": f"Is {curr_val} > {max_val}? -> {'Yes' if is_greater else 'No'}"
            })

            # Step B: Update if greater
            if is_greater:
                max_val = curr_val
                val_history.append(max_val)
                steps.append({
                    "step": len(steps) + 1,
                    "line": 5,
                    "caption": f"arr[{i}] ({curr_val}) is strictly greater! Updated maxVal = {curr_val}",
                    "variables": {"i": i, "arr[i]": curr_val, "maxVal": max_val, "n": n},
                    "value_history": {"maxVal": list(val_history)},
                    "pointers": {"i": i, "max": i},
                    "array_data": [{"val": v, "idx": idx, "highlight": "updated" if idx == i else "none"} for idx, v in enumerate(arr)],
                    "note": f"New maximum found: {max_val}"
                })

        steps.append({
            "step": len(steps) + 1,
            "line": 8,
            "caption": f"Loop completed. Returning final maximum: {max_val}",
            "variables": {"return_value": max_val},
            "value_history": {"maxVal": list(val_history)},
            "pointers": {},
            "array_data": [{"val": v, "idx": idx, "highlight": "active" if v == max_val else "none"} for idx, v in enumerate(arr)],
            "note": f"Result: {max_val}"
        })

    # =========================================================================
    # Problem 2: Sum of Array Elements
    # =========================================================================
    elif problem_id == 2:
        is_sub = "-=" in code_clean and not is_model_solution
        sum_val = 0
        val_history = [0]

        steps.append({
            "step": 1,
            "line": 2,
            "caption": "Initialize accumulator sum = 0",
            "variables": {"sum": 0, "n": n},
            "value_history": {"sum": list(val_history)},
            "pointers": {},
            "array_data": [{"val": v, "idx": i, "highlight": "none"} for i, v in enumerate(arr)],
            "note": "Ready to iterate"
        })

        for i in range(len(arr)):
            curr_val = arr[i]
            if is_sub:
                sum_val -= curr_val
            else:
                sum_val += curr_val
            val_history.append(sum_val)

            steps.append({
                "step": len(steps) + 1,
                "line": 4,
                "caption": f"i = {i}: {'sum -= ' if is_sub else 'sum += '} arr[{i}] ({curr_val}) -> sum is now {sum_val}",
                "variables": {"i": i, "arr[i]": curr_val, "sum": sum_val, "n": n},
                "value_history": {"sum": list(val_history)},
                "pointers": {"i": i},
                "array_data": [{"val": v, "idx": idx, "highlight": "active" if idx == i else "none"} for idx, v in enumerate(arr)],
                "note": f"Accumulated: {sum_val}"
            })

        steps.append({
            "step": len(steps) + 1,
            "line": 6,
            "caption": f"Traversal finished. Returning total sum: {sum_val}",
            "variables": {"return_value": sum_val},
            "value_history": {"sum": list(val_history)},
            "pointers": {},
            "array_data": [{"val": v, "idx": idx, "highlight": "none"} for idx, v in enumerate(arr)],
            "note": f"Final sum: {sum_val}"
        })

    # =========================================================================
    # Problem 3: Reverse Array In-Place
    # =========================================================================
    elif problem_id == 3:
        curr_arr = list(arr)
        left = 0
        right = len(curr_arr) - 1

        steps.append({
            "step": 1,
            "line": 2,
            "caption": f"Initialize two pointers: left = 0, right = {right}",
            "variables": {"left": left, "right": right, "n": n},
            "value_history": {},
            "pointers": {"left": left, "right": right},
            "array_data": [{"val": v, "idx": i, "highlight": "none"} for i, v in enumerate(curr_arr)],
            "note": "Start two-pointer reversal"
        })

        while left < right:
            # Comparison step
            steps.append({
                "step": len(steps) + 1,
                "line": 4,
                "caption": f"left ({left}) < right ({right}): Swapping arr[{left}] ({curr_arr[left]}) and arr[{right}] ({curr_arr[right]})",
                "variables": {"left": left, "right": right},
                "value_history": {},
                "pointers": {"left": left, "right": right},
                "array_data": [{"val": v, "idx": i, "highlight": "swapping" if i in (left, right) else "none"} for i, v in enumerate(curr_arr)],
                "note": "Swapping symmetric elements"
            })

            # Swap
            curr_arr[left], curr_arr[right] = curr_arr[right], curr_arr[left]

            steps.append({
                "step": len(steps) + 1,
                "line": 7,
                "caption": f"Swapped! Advance left to {left + 1}, decrement right to {right - 1}",
                "variables": {"left": left + 1, "right": right - 1},
                "value_history": {},
                "pointers": {"left": left + 1, "right": right - 1},
                "array_data": [{"val": v, "idx": i, "highlight": "updated" if i in (left, right) else "none"} for i, v in enumerate(curr_arr)],
                "note": "Pointers move inward"
            })

            left += 1
            right -= 1

        steps.append({
            "step": len(steps) + 1,
            "line": 10,
            "caption": "Reversal in-place complete!",
            "variables": {"result": " ".join(map(str, curr_arr))},
            "value_history": {},
            "pointers": {},
            "array_data": [{"val": v, "idx": i, "highlight": "active"} for i, v in enumerate(curr_arr)],
            "note": "Array successfully reversed"
        })

    # =========================================================================
    # Problem 4: Second Largest Element
    # =========================================================================
    elif problem_id == 4:
        first = -1
        second = -1
        val_history_first = [-1]
        val_history_second = [-1]

        steps.append({
            "step": 1,
            "line": 3,
            "caption": "Initialize first = -1 (largest) and second = -1 (second largest)",
            "variables": {"first": -1, "second": -1, "n": n},
            "value_history": {"first": list(val_history_first), "second": list(val_history_second)},
            "pointers": {},
            "array_data": [{"val": v, "idx": i, "highlight": "none"} for i, v in enumerate(arr)],
            "note": "Tracking top 2 distinct elements"
        })

        for i, val in enumerate(arr):
            if val > first:
                second = first
                first = val
                val_history_first.append(first)
                val_history_second.append(second)
                caption = f"i = {i} ({val} > first {second}): second becomes {second}, first becomes {first}"
            elif val > second and val != first:
                second = val
                val_history_second.append(second)
                caption = f"i = {i} ({val} > second {second} and != first): second becomes {second}"
            else:
                caption = f"i = {i} ({val}): No update needed"

            steps.append({
                "step": len(steps) + 1,
                "line": 6,
                "caption": caption,
                "variables": {"i": i, "arr[i]": val, "first": first, "second": second},
                "value_history": {"first": list(val_history_first), "second": list(val_history_second)},
                "pointers": {"i": i},
                "array_data": [{"val": v, "idx": idx, "highlight": "active" if v in (first, second) else "none"} for idx, v in enumerate(arr)],
                "note": f"State: first={first}, second={second}"
            })

        steps.append({
            "step": len(steps) + 1,
            "line": 13,
            "caption": f"Returning second largest element: {second}",
            "variables": {"return_value": second},
            "value_history": {"first": list(val_history_first), "second": list(val_history_second)},
            "pointers": {},
            "array_data": [{"val": v, "idx": idx, "highlight": "active" if v == second else "none"} for idx, v in enumerate(arr)],
            "note": f"Result: {second}"
        })

    # =========================================================================
    # Problem 5: Count Occurrences
    # =========================================================================
    elif problem_id == 5:
        target_val = target if target is not None else (arr[0] if arr else 0)
        count = 0
        val_history = [0]

        steps.append({
            "step": 1,
            "line": 2,
            "caption": f"Initialize count = 0, searching for target = {target_val}",
            "variables": {"count": 0, "target": target_val, "n": n},
            "value_history": {"count": list(val_history)},
            "pointers": {},
            "array_data": [{"val": v, "idx": i, "highlight": "none"} for i, v in enumerate(arr)],
            "note": f"Target: {target_val}"
        })

        for i, val in enumerate(arr):
            is_match = (val == target_val)
            if is_match:
                count += 1
                val_history.append(count)
                caption = f"i = {i}: arr[{i}] ({val}) == target ({target_val})! Incremented count to {count}"
            else:
                caption = f"i = {i}: arr[{i}] ({val}) != target ({target_val})"

            steps.append({
                "step": len(steps) + 1,
                "line": 4,
                "caption": caption,
                "variables": {"i": i, "arr[i]": val, "count": count, "target": target_val},
                "value_history": {"count": list(val_history)},
                "pointers": {"i": i},
                "array_data": [{"val": v, "idx": idx, "highlight": "active" if (idx == i and is_match) else ("comparing" if idx == i else "none")} for idx, v in enumerate(arr)],
                "note": f"Matches so far: {count}"
            })

        steps.append({
            "step": len(steps) + 1,
            "line": 8,
            "caption": f"Finished scanning array. Total occurrences: {count}",
            "variables": {"return_value": count},
            "value_history": {"count": list(val_history)},
            "pointers": {},
            "array_data": [{"val": v, "idx": idx, "highlight": "active" if v == target_val else "none"} for idx, v in enumerate(arr)],
            "note": f"Result: {count}"
        })

    # =========================================================================
    # Problem 6: Sum Linked List Values
    # =========================================================================
    elif problem_id == 6:
        total = 0
        val_history = [0]
        ll_nodes = [{"id": i, "val": v, "next_id": i + 1 if i + 1 < len(arr) else None} for i, v in enumerate(arr)]

        steps.append({
            "step": 1,
            "line": 2,
            "caption": "Initialize total = 0, curr pointer pointing to head node",
            "variables": {"total": 0, "curr": f"Node({arr[0]})" if arr else "NULL"},
            "value_history": {"total": list(val_history)},
            "pointers": {"curr": 0 if arr else None},
            "linked_list_data": ll_nodes,
            "note": "Start at head"
        })

        for i, val in enumerate(arr):
            total += val
            val_history.append(total)

            steps.append({
                "step": len(steps) + 1,
                "line": 5,
                "caption": f"Visit Node({val}): total += curr->val ({val}) -> total is now {total}. Move curr = curr->next",
                "variables": {"curr->val": val, "total": total},
                "value_history": {"total": list(val_history)},
                "pointers": {"curr": i},
                "linked_list_data": ll_nodes,
                "note": f"Current node: {val}"
            })

        steps.append({
            "step": len(steps) + 1,
            "line": 8,
            "caption": f"curr reached NULL. Returning total sum: {total}",
            "variables": {"return_value": total, "curr": "NULL"},
            "value_history": {"total": list(val_history)},
            "pointers": {"curr": None},
            "linked_list_data": ll_nodes,
            "note": f"Sum: {total}"
        })

    # =========================================================================
    # Problem 7: Reverse a Linked List
    # =========================================================================
    elif problem_id == 7:
        ll_nodes = [{"id": i, "val": v, "next_id": i + 1 if i + 1 < len(arr) else None} for i, v in enumerate(arr)]
        
        steps.append({
            "step": 1,
            "line": 2,
            "caption": "Initialize prev = NULL, curr = head",
            "variables": {"prev": "NULL", "curr": f"Node({arr[0]})" if arr else "NULL"},
            "value_history": {},
            "pointers": {"prev": None, "curr": 0 if arr else None},
            "linked_list_data": [dict(n) for n in ll_nodes],
            "note": "Reversal pointers ready"
        })

        curr_nodes = [dict(n) for n in ll_nodes]
        for i in range(len(arr)):
            # Save nextNode
            next_idx = i + 1 if i + 1 < len(arr) else None
            # Redirect arrow
            curr_nodes[i]["next_id"] = i - 1 if i > 0 else None

            steps.append({
                "step": len(steps) + 1,
                "line": 5,
                "caption": f"Node({arr[i]}): nextNode = curr->next, redirect curr->next = prev ({'Node(' + str(arr[i-1]) + ')' if i > 0 else 'NULL'})",
                "variables": {"curr": f"Node({arr[i]})", "prev": f"Node({arr[i-1]})" if i > 0 else "NULL", "nextNode": f"Node({arr[next_idx]})" if next_idx is not None else "NULL"},
                "value_history": {},
                "pointers": {"curr": i, "prev": i - 1 if i > 0 else None, "next": next_idx},
                "linked_list_data": [dict(n) for n in curr_nodes],
                "note": f"Reversed link at Node({arr[i]})"
            })

        steps.append({
            "step": len(steps) + 1,
            "line": 10,
            "caption": f"curr reached NULL. prev now points to new head: Node({arr[-1] if arr else 'NULL'})",
            "variables": {"new_head": f"Node({arr[-1]})" if arr else "NULL"},
            "value_history": {},
            "pointers": {"head": len(arr) - 1 if arr else None},
            "linked_list_data": [dict(n) for n in curr_nodes],
            "note": "Reversal complete"
        })

    # =========================================================================
    # Problem 8: Find Middle Node Value
    # =========================================================================
    elif problem_id == 8:
        ll_nodes = [{"id": i, "val": v, "next_id": i + 1 if i + 1 < len(arr) else None} for i, v in enumerate(arr)]
        slow = 0
        fast = 0

        steps.append({
            "step": 1,
            "line": 3,
            "caption": "Initialize slow = head, fast = head (Tortoise & Hare)",
            "variables": {"slow": f"Node({arr[0]})", "fast": f"Node({arr[0]})"},
            "value_history": {},
            "pointers": {"slow": 0, "fast": 0},
            "linked_list_data": ll_nodes,
            "note": "Two pointers at head"
        })

        while fast < len(arr) and fast + 1 < len(arr):
            slow += 1
            fast += 2
            steps.append({
                "step": len(steps) + 1,
                "line": 6,
                "caption": f"Advance slow by 1 -> Node({arr[slow]}), fast by 2 -> {'Node(' + str(arr[fast]) + ')' if fast < len(arr) else 'NULL'}",
                "variables": {"slow": f"Node({arr[slow]})", "fast": f"Node({arr[fast]})" if fast < len(arr) else "NULL"},
                "value_history": {},
                "pointers": {"slow": slow, "fast": fast if fast < len(arr) else None},
                "linked_list_data": ll_nodes,
                "note": f"slow at {arr[slow]}"
            })

        steps.append({
            "step": len(steps) + 1,
            "line": 9,
            "caption": f"fast reached end. Middle node is slow: Node({arr[slow]}), returning value {arr[slow]}",
            "variables": {"return_value": arr[slow]},
            "value_history": {},
            "pointers": {"slow": slow},
            "linked_list_data": ll_nodes,
            "note": f"Middle value: {arr[slow]}"
        })

    # =========================================================================
    # Problem 9: Count Nodes in List
    # =========================================================================
    elif problem_id == 9:
        count = 0
        val_history = [0]
        ll_nodes = [{"id": i, "val": v, "next_id": i + 1 if i + 1 < len(arr) else None} for i, v in enumerate(arr)]

        steps.append({
            "step": 1,
            "line": 2,
            "caption": "Initialize count = 0, curr = head",
            "variables": {"count": 0, "curr": f"Node({arr[0]})" if arr else "NULL"},
            "value_history": {"count": list(val_history)},
            "pointers": {"curr": 0 if arr else None},
            "linked_list_data": ll_nodes,
            "note": "Counting start"
        })

        for i, val in enumerate(arr):
            count += 1
            val_history.append(count)
            steps.append({
                "step": len(steps) + 1,
                "line": 5,
                "caption": f"Visit Node({val}): increment count to {count}, advance curr = curr->next",
                "variables": {"count": count, "curr->val": val},
                "value_history": {"count": list(val_history)},
                "pointers": {"curr": i},
                "linked_list_data": ll_nodes,
                "note": f"Count: {count}"
            })

        steps.append({
            "step": len(steps) + 1,
            "line": 8,
            "caption": f"curr reached NULL. Total node count: {count}",
            "variables": {"return_value": count},
            "value_history": {"count": list(val_history)},
            "pointers": {"curr": None},
            "linked_list_data": ll_nodes,
            "note": f"Total: {count}"
        })

    # =========================================================================
    # Problem 10: Detect Value in List
    # =========================================================================
    elif problem_id == 10:
        target_val = target if target is not None else (arr[0] if arr else 0)
        found = 0
        ll_nodes = [{"id": i, "val": v, "next_id": i + 1 if i + 1 < len(arr) else None} for i, v in enumerate(arr)]

        steps.append({
            "step": 1,
            "line": 2,
            "caption": f"Start search for target = {target_val}, curr = head",
            "variables": {"target": target_val, "curr": f"Node({arr[0]})" if arr else "NULL"},
            "value_history": {},
            "pointers": {"curr": 0 if arr else None},
            "linked_list_data": ll_nodes,
            "note": f"Searching for {target_val}"
        })

        for i, val in enumerate(arr):
            if val == target_val:
                found = 1
                steps.append({
                    "step": len(steps) + 1,
                    "line": 4,
                    "caption": f"Node({val}) matches target ({target_val})! Returning 1 immediately.",
                    "variables": {"curr->val": val, "target": target_val, "return_value": 1},
                    "value_history": {},
                    "pointers": {"curr": i},
                    "linked_list_data": ll_nodes,
                    "note": "Target detected"
                })
                break
            else:
                steps.append({
                    "step": len(steps) + 1,
                    "line": 6,
                    "caption": f"Node({val}) != target ({target_val}), move curr = curr->next",
                    "variables": {"curr->val": val, "target": target_val},
                    "value_history": {},
                    "pointers": {"curr": i},
                    "linked_list_data": ll_nodes,
                    "note": "Continuing search"
                })

        if not found:
            steps.append({
                "step": len(steps) + 1,
                "line": 9,
                "caption": f"Reached NULL without finding target ({target_val}). Returning 0.",
                "variables": {"return_value": 0},
                "value_history": {},
                "pointers": {"curr": None},
                "linked_list_data": ll_nodes,
                "note": "Target not present"
            })

    # Generic Fallback
    if not steps:
        steps.append({
            "step": 1,
            "line": 1,
            "caption": "Executing C program with test input",
            "variables": {"n": n},
            "value_history": {},
            "pointers": {},
            "array_data": [{"val": v, "idx": i, "highlight": "none"} for i, v in enumerate(arr)],
            "note": "Initial step"
        })

    return {
        "problem_id": problem_id,
        "input": input_str,
        "is_model": is_model_solution,
        "steps": steps
    }

def detect_pattern_error(code: str, problem_id: int, input_str: str, expected_out: str, actual_out: str) -> Tuple[str, str]:
    """
    Detects classic C logic bugs via static and runtime patterns.
    Returns (error_type, plain_reason).
    """
    code_clean = re.sub(r'//.*', '', code)
    code_clean = re.sub(r'/\*.*?\*/', '', code_clean, flags=re.DOTALL)

    # 1. Assignment in conditional (= vs ==)
    if re.search(r'\bif\s*\(\s*[a-zA-Z_]\w*\s*=\s*[^=]', code_clean):
        return (
            "assignment_in_condition",
            "Found '=' (assignment) inside an 'if' condition. In C, single '=' assigns a value instead of comparing. Use '==' for equality checks."
        )

    # 2. Sign error (e.g. subtracting instead of adding)
    if problem_id in (2, 6):
        if "-=" in code_clean or "- arr[" in code_clean or "- curr->val" in code_clean:
            return (
                "sign_error",
                "Your accumulator subtracted values instead of adding them (e.g. '-=' instead of '+='), causing the total to become negative or lower than expected."
            )

    # 3. Off-by-one loop bound
    if re.search(r'for\s*\(\s*int\s+\w+\s*=\s*0\s*;\s*\w+\s*<=\s*n\s*;', code_clean) or re.search(r'for\s*\(\s*\w+\s*=\s*0\s*;\s*\w+\s*<=\s*n\s*;', code_clean):
        return (
            "off_by_one",
            "Loop condition uses '<= n' instead of '< n'. In C, arrays of size n only have valid indices from 0 to n - 1. Index n is out of bounds."
        )

    # 4. Off-by-one start index
    if problem_id in (2, 5) and re.search(r'for\s*\(\s*(?:int\s+)?\w+\s*=\s*1\s*;', code_clean):
        return (
            "off_by_one_start",
            "The loop starts at index 1 ('i = 1'), skipping the first element (index 0). C arrays start at index 0."
        )

    # 5. Wrong initial value
    if problem_id == 1:
        if re.search(r'(?:int\s+)?(?:max|maxVal)\s*=\s*0\s*;', code_clean):
            return (
                "wrong_initial_value",
                "You initialized your maximum variable to 0. If the array contains only negative numbers (like [-10, -3]), 0 is incorrectly returned because 0 is larger than any negative number. Initialize to arr[0] instead."
            )

    # 6. Integer division truncation
    if "/" in code_clean and "float" in code_clean and not ("(float)" in code_clean or "(double)" in code_clean or ".0" in code_clean):
        return (
            "integer_division",
            "Dividing two integers in C performs integer truncation before assigning to a float/double. Cast one operand to (float) or (double)."
        )

    # 7. Missing return statement
    if "return " not in code_clean and "void " not in code_clean:
        return (
            "missing_return",
            "Your non-void function does not explicitly return a value at the end of all execution paths."
        )

    # 8. Unhandled empty / NULL base case
    if "head == NULL" not in code_clean and "n == 0" not in code_clean and ("0" in input_str or "NULL" in input_str):
        return (
            "null_pointer_edge_case",
            "Your code did not handle the empty list or zero-length array edge case (e.g. head == NULL or n == 0)."
        )

    return (
        "logic_mismatch",
        f"Output mismatch: expected '{expected_out}', but your code generated '{actual_out}'."
    )

def explain_divergence(
    student_code: str,
    problem_id: int,
    input_str: str,
    expected_output: str,
    actual_output: str
) -> Dict[str, Any]:
    """
    Compares student execution with model solution, identifies the first
    divergent step, and returns side-by-side animation steps.
    """
    error_type, reason = detect_pattern_error(
        student_code, problem_id, input_str, expected_output, actual_output
    )

    student_trace = trace_problem(problem_id, student_code, input_str, is_model_solution=False)
    model_trace = trace_problem(problem_id, "", input_str, is_model_solution=True)

    student_steps = student_trace["steps"]
    model_steps = model_trace["steps"]

    divergent_step_idx = None
    min_len = min(len(student_steps), len(model_steps))
    
    for i in range(min_len):
        s_vars = student_steps[i].get("variables", {})
        m_vars = model_steps[i].get("variables", {})
        # Check if values differ
        for k in s_vars:
            if k in m_vars and s_vars[k] != m_vars[k]:
                divergent_step_idx = i
                student_steps[i]["is_divergent"] = True
                student_steps[i]["divergence_reason"] = f"At this step, '{k}' became {s_vars[k]} in your code, but was expected to be {m_vars[k]}."
                break
        if divergent_step_idx is not None:
            break

    if divergent_step_idx is None and student_steps:
        divergent_step_idx = len(student_steps) - 1
        student_steps[-1]["is_divergent"] = True
        student_steps[-1]["divergence_reason"] = f"Final return value '{actual_output}' diverged from expected '{expected_output}'."

    return {
        "error_type": error_type,
        "explanation": reason,
        "expected_output": expected_output,
        "actual_output": actual_output,
        "divergent_step_index": divergent_step_idx,
        "trace_steps": student_steps,
        "model_trace_steps": model_steps
    }

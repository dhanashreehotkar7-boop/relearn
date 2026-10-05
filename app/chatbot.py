"""
Re:Learn - AI C Assistant Chatbot
Provides contextual hints, error breakdowns, and conceptual coaching without spoiling solutions.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

def get_gemini_api_key() -> Optional[str]:
    # Check env or .env file
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key.strip()
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return None

def generate_rule_based_response(
    query_type: str,
    problem_title: str,
    problem_desc: str,
    student_code: str,
    error_info: Optional[Dict[str, Any]],
    is_solved: bool
) -> str:
    """Intelligent fallback coaching responses when Gemini API key is not configured."""
    q_lower = query_type.lower()

    if "explain this problem" in q_lower or "explain problem" in q_lower:
        if "maximum" in problem_title.lower():
            return f"**Understanding {problem_title}**:\n\nYou need to find the largest integer in a given array.\n\n💡 **Key Things to Remember**:\n- What happens if all numbers are negative (e.g. `[-5, -2, -9]`)? Starting your max at `0` would give a wrong answer!\n- Start by assuming the first element (`arr[0]`) is the largest, then check the rest."
        elif "sum" in problem_title.lower() and "list" in problem_title.lower():
            return f"**Understanding {problem_title}**:\n\nYou are given the starting pointer `head` to a singly linked list. Your job is to visit each node, read its `val`, add it to a total accumulator, and return that total.\n\n⚠️ Don't forget to check if `head == NULL`!"
        elif "reverse" in problem_title.lower() and "list" in problem_title.lower():
            return f"**Understanding {problem_title}**:\n\nYou need to turn arrows around in-place: `1 -> 2 -> 3` becomes `3 -> 2 -> 1`.\n\n💡 **Three-pointer strategy**: Use `prev`, `curr`, and `nextNode` to redirect each node's `next` pointer without losing the rest of the list."
        else:
            return f"**Problem Overview for {problem_title}**:\n\nReview the input format and constraints carefully. Think about edge cases like an empty array/list or single-element inputs."

    if "explain my error" in q_lower or "explain error" in q_lower:
        if error_info:
            diag = error_info.get("diagnostic") or error_info.get("explanation")
            etype = error_info.get("error_type", "")
            if diag:
                return f"🔍 **Error Analysis**:\n\n{diag}\n\n💡 **Tip**: Review the line indicated in the editor and ensure syntax, types, and semicolons are accurate."
            if "off_by_one" in etype:
                return "🔍 **Off-by-One Loop Bug Detected**:\n\nIn C, array indexing is zero-based: indices go from `0` to `n - 1`. If your loop condition is `i <= n`, accessing `arr[n]` will read uninitialized memory!"
            if "assignment_in_condition" in etype:
                return "🔍 **Assignment inside 'if' statement**:\n\nYou wrote `if (x = y)` instead of `if (x == y)`. A single `=` assigns the value, which evaluates to true if non-zero!"
        return "You haven't run into a specific compiler error yet. Click **Run Tests** to see how your code performs!"

    # Default hint
    if "maximum" in problem_title.lower():
        return "💡 **Hint**: Initialize `int maxVal = arr[0];` and iterate from `i = 1` up to `i < n`. Compare each `arr[i] > maxVal`."
    elif "sum" in problem_title.lower() and "array" in problem_title.lower():
        return "💡 **Hint**: Initialize an accumulator `int sum = 0;`, then loop with `for (int i = 0; i < n; i++) sum += arr[i];` and return `sum`."
    elif "reverse" in problem_title.lower() and "array" in problem_title.lower():
        return "💡 **Hint**: Use two indices: `int left = 0, right = n - 1;`. Swap `arr[left]` and `arr[right]` using a temporary variable while `left < right`."
    elif "second" in problem_title.lower():
        return "💡 **Hint**: Keep track of two variables: `first` and `second`, both initialized to `-1`. When you find a number larger than `first`, update `second = first` first, then `first = arr[i]`."
    elif "middle" in problem_title.lower():
        return "💡 **Hint**: The classic algorithm uses two pointers: `slow` and `fast`. While `fast != NULL && fast->next != NULL`, advance `slow = slow->next` and `fast = fast->next->next`."
    elif "detect" in problem_title.lower() or "count" in problem_title.lower():
        return "💡 **Hint**: Use a pointer `struct Node* curr = head;` and loop `while (curr != NULL)`. Check `curr->val` at each step and advance `curr = curr->next`."

    return "💡 **Coaching Hint**: Break the problem down step-by-step. Trace your variables with a small example on paper (e.g. `[1, 2, 3]`)."

def chat_with_assistant(
    prompt: str,
    problem_title: str,
    problem_desc: str,
    student_code: str,
    error_info: Optional[Dict[str, Any]],
    is_solved: bool
) -> str:
    """Queries Gemini if configured, otherwise uses intelligent rule-based coaching."""
    api_key = get_gemini_api_key()
    if not api_key:
        return generate_rule_based_response(
            prompt, problem_title, problem_desc, student_code, error_info, is_solved
        )

    system_instruction = (
        "You are an encouraging and expert C programming tutor for Re:Learn. "
        "Your goal is to guide the student toward understanding the underlying C memory, syntax, and logic concepts. "
        f"CRITICAL RULE: {'You may explain the solution in full because the student has solved the problem.' if is_solved else 'DO NOT provide the full solution code. Offer hints, identify misconceptions, and ask guiding questions.'} "
        "Keep your response concise (under 150 words), formatted nicely in markdown."
    )

    user_context = (
        f"Problem: {problem_title}\n"
        f"Student's Current C Code:\n```c\n{student_code}\n```\n"
        f"Latest Error/Status: {json.dumps(error_info or {})}\n"
        f"Student Query: {prompt}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"{system_instruction}\n\n{user_context}"}]}
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 300
        }
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidates = res_data.get("candidates", [])
            if candidates:
                text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if text:
                    return text.strip()
    except Exception:
        pass

    return generate_rule_based_response(
        prompt, problem_title, problem_desc, student_code, error_info, is_solved
    )

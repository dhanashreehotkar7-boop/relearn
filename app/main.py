import math
import os
import sqlite3
import tempfile
import time
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Header, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from app.database import init_db, get_db_connection
from app.auth import hash_password, verify_password
from app.runner import (
    compile_and_run,
    compile_c_source,
    run_c_executable,
    parse_gcc_errors,
    get_friendly_explanation
)
from app.harness import generate_harness, map_error_line_to_student
from app.tracer import explain_divergence
from app.chatbot import chat_with_assistant
from app.relearn_agent import ReLearnAgent

app = FastAPI(title="Re:Learn - LeetCode C Practice Platform")
agent = ReLearnAgent()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# ==========================================
# Pydantic Request Models
# ==========================================
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class CodeExecutionRequest(BaseModel):
    student_id: int
    code: str
    started_at_ms: int
    submitted_at_ms: int
    error_shown_ms: Optional[int] = None
    last_error_type: Optional[str] = None

class ChatRequest(BaseModel):
    message: Optional[str] = None
    problem_id: Optional[int] = None
    prompt: Optional[str] = None
    code: Optional[str] = None
    student_id: Optional[int] = None
    error_info: Optional[Dict[str, Any]] = None

class CoachRequest(BaseModel):
    mode: str = "chat"
    problem: str = ""
    code: str = ""
    output: str = ""
    question: str = ""
    problem_id: Optional[int] = None
    student_id: Optional[int] = None

class TeachRequest(BaseModel):
    key: str
    value: str

class AgentChatRequest(BaseModel):
    message: str
    student_id: Optional[int] = None
    context: Optional[Dict[str, Any]] = None

class CardReviewRequest(BaseModel):
    student_id: int
    rating: str  # 'got_it' or 'again'

@app.on_event("startup")
def on_startup():
    init_db()

# ==========================================
# Auth & Profile Endpoints
# ==========================================
@app.post("/api/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest):
    name = req.name.strip()
    email = req.email.strip().lower()
    password = req.password

    if not name:
        raise HTTPException(status_code=400, detail="Full name cannot be empty.")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM student WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Email is already registered.")

    pwd_hash = hash_password(password)
    today_str = date.today().isoformat()
    try:
        cursor.execute(
            """INSERT INTO student (name, email, password_hash, xp, level, streak, last_active_date)
               VALUES (?, ?, ?, 0, 1, 1, ?)""",
            (name, email, pwd_hash, today_str)
        )
        conn.commit()
        user_id = cursor.lastrowid

        seed_user_flashcards(cursor, user_id)
        conn.commit()
        conn.close()

        return {
            "ok": True,
            "message": "Account created successfully!",
            "user": {
                "id": user_id,
                "name": name,
                "email": email,
                "xp": 0,
                "level": 1,
                "streak": 1
            }
        }
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/login")
def login(req: LoginRequest):
    email = req.email.strip().lower()
    password = req.password

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM student WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    today_str = date.today().isoformat()
    last_active = user["last_active_date"]
    streak = user["streak"] or 1
    if last_active and last_active != today_str:
        try:
            last_date = date.fromisoformat(last_active)
            diff = (date.today() - last_date).days
            if diff == 1:
                streak += 1
            elif diff > 1:
                streak = 1
        except Exception:
            streak = 1

    cursor.execute(
        "UPDATE student SET streak = ?, last_active_date = ? WHERE id = ?",
        (streak, today_str, user["id"])
    )
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "message": "Login successful!",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "xp": user["xp"],
            "level": user["level"],
            "streak": streak
        }
    }

@app.get("/api/user/profile")
def get_user_profile(student_id: int = Query(...)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, email, xp, level, streak FROM student WHERE id = ?", (student_id,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="Student not found.")

    cursor.execute("SELECT COUNT(DISTINCT problem_id) FROM problem_session WHERE student_id = ? AND solved_at_ms IS NOT NULL", (student_id,))
    solved_count = cursor.fetchone()[0]

    cursor.execute("SELECT badge_key, badge_name, badge_desc, icon, awarded_at FROM student_badge WHERE student_id = ?", (student_id,))
    badges = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {
        "user": dict(user),
        "solved_count": solved_count,
        "badges": badges
    }

# ==========================================
# Problems API
# ==========================================
@app.get("/api/problems")
def get_problems_list(student_id: Optional[int] = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, topic, difficulty, time_complexity, space_complexity
        FROM problem
        ORDER BY topic ASC, id ASC
    """)
    problems = [dict(row) for row in cursor.fetchall()]

    solved_set = set()
    best_times = {}
    if student_id:
        cursor.execute("SELECT problem_id, total_time_ms FROM problem_session WHERE student_id = ? AND solved_at_ms IS NOT NULL", (student_id,))
        for row in cursor.fetchall():
            solved_set.add(row["problem_id"])
            best_times[row["problem_id"]] = row["total_time_ms"]

    conn.close()

    for p in problems:
        p["is_solved"] = p["id"] in solved_set
        p["best_time_ms"] = best_times.get(p["id"])

    return {"problems": problems}

@app.get("/api/problems/{problem_id}")
def get_problem_detail(problem_id: int, student_id: Optional[int] = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM problem WHERE id = ?", (problem_id,))
    p = cursor.fetchone()
    if not p:
        conn.close()
        raise HTTPException(status_code=404, detail="Problem not found.")

    prob_dict = dict(p)

    cursor.execute("SELECT id, input, expected_output FROM test_case WHERE problem_id = ? AND is_hidden = 0 ORDER BY id ASC", (problem_id,))
    public_cases = [dict(row) for row in cursor.fetchall()]
    prob_dict["public_test_cases"] = public_cases

    is_solved = False
    if student_id:
        cursor.execute("SELECT solved_at_ms FROM problem_session WHERE student_id = ? AND problem_id = ?", (student_id, problem_id))
        sess = cursor.fetchone()
        if sess and sess["solved_at_ms"]:
            is_solved = True

    prob_dict["is_solved"] = is_solved
    if not is_solved:
        prob_dict["model_solution"] = None
        prob_dict["solution_explanation"] = None

    conn.close()
    return prob_dict

# ==========================================
# Code Execution & Testing (Run / Submit)
# ==========================================
@app.post("/api/problems/{problem_id}/run")
def run_code(problem_id: int, req: CodeExecutionRequest):
    return execute_problem_code(problem_id, req, run_hidden=False)

@app.post("/api/problems/{problem_id}/submit")
def submit_code(problem_id: int, req: CodeExecutionRequest):
    return execute_problem_code(problem_id, req, run_hidden=True)

def execute_problem_code(problem_id: int, req: CodeExecutionRequest, run_hidden: bool) -> Dict[str, Any]:
    student_id = req.student_id
    student_code = req.code
    code_lines_count = len(student_code.splitlines())

    # Step 1: Read-only DB pass to get test cases and record session start
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT OR IGNORE INTO problem_session (student_id, problem_id, first_opened_ms, total_time_ms)
           VALUES (?, ?, ?, 0)""",
        (student_id, problem_id, req.started_at_ms)
    )
    conn.commit()

    if run_hidden:
        cursor.execute("SELECT id, input, expected_output, is_hidden FROM test_case WHERE problem_id = ? ORDER BY id ASC", (problem_id,))
    else:
        cursor.execute("SELECT id, input, expected_output, is_hidden FROM test_case WHERE problem_id = ? AND is_hidden = 0 ORDER BY id ASC", (problem_id,))
    test_cases = [dict(r) for r in cursor.fetchall()]
    conn.close()  # Close DB immediately during compilation and execution!

    if not test_cases:
        raise HTTPException(status_code=500, detail="No test cases configured for this problem.")

    # Step 2: Generate Wrapped C Code & Compile ONCE in isolated tempdir
    full_c_code, line_offset = generate_harness(problem_id, student_code)
    duration_ms = max(1, req.submitted_at_ms - req.started_at_ms)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        compile_ok, exe_file, compile_stderr, diagnostics = compile_c_source(full_c_code, tmp_path, timeout_compile=10.0)

        # Handle Compile Error
        if not compile_ok or exe_file is None:
            mapped_diagnostics = []
            first_error_line = None
            for d in diagnostics:
                m_line = map_error_line_to_student(d.line, line_offset, code_lines_count)
                if first_error_line is None and d.kind == "error":
                    first_error_line = m_line
                mapped_diagnostics.append({
                    "line": m_line,
                    "raw_line": d.line,
                    "column": d.column,
                    "kind": d.kind,
                    "message": d.message,
                    "friendly_explanation": d.friendly_explanation
                })

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO attempt (student_id, problem_id, code, status, error_line, error_type, started_at_ms, submitted_at_ms, duration_ms)
                   VALUES (?, ?, ?, 'compile_error', ?, 'compile_error', ?, ?, ?)""",
                (student_id, problem_id, student_code, first_error_line, req.started_at_ms, req.submitted_at_ms, duration_ms)
            )
            attempt_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return {
                "status": "compile_error",
                "is_accepted": False,
                "stage": "compile",
                "error_line": first_error_line or 1,
                "error_type": "compile_error",
                "diagnostics": mapped_diagnostics,
                "raw_stderr": compile_stderr,
                "attempt_id": attempt_id
            }

        # Step 3: Run compiled binary against each test case fast
        results = []
        all_passed = True
        failing_case = None

        for tc in test_cases:
            tc_id = tc["id"]
            tc_input = tc["input"]
            expected = tc["expected_output"].strip()
            is_hidden = bool(tc["is_hidden"])

            run_res = run_c_executable(exe_file, tc_input, tmp_path, timeout_exec=2.0)
            actual = run_res.stdout.strip()

            if run_res.stage == "timeout":
                all_passed = False
                failing_case = (tc_input, expected, "Timeout (>2.0s)", "timeout")
                results.append({
                    "test_case_id": tc_id,
                    "passed": False,
                    "is_hidden": is_hidden,
                    "input": tc_input if not is_hidden else "(Hidden test case)",
                    "expected": expected if not is_hidden else "(Hidden)",
                    "actual": "Time Limit Exceeded (>2.0s)",
                    "stage": "timeout"
                })
                break

            if not run_res.success:
                all_passed = False
                failing_case = (tc_input, expected, "Runtime Crash / Segfault", "runtime_error")
                results.append({
                    "test_case_id": tc_id,
                    "passed": False,
                    "is_hidden": is_hidden,
                    "input": tc_input if not is_hidden else "(Hidden test case)",
                    "expected": expected if not is_hidden else "(Hidden)",
                    "actual": f"Runtime Error (exit code {run_res.return_code})",
                    "stage": "runtime_error"
                })
                break

            passed = (actual == expected)
            if not passed:
                all_passed = False
                if failing_case is None:
                    failing_case = (tc_input, expected, actual, "wrong_answer")

            results.append({
                "test_case_id": tc_id,
                "passed": passed,
                "is_hidden": is_hidden,
                "input": tc_input if not is_hidden else "(Hidden test case)",
                "expected": expected if not is_hidden else "(Hidden)",
                "actual": actual if not is_hidden else "(Hidden)",
                "stage": "execute"
            })

    # Step 4: Record Results & Gamification in Database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Track Error Fix Time
    if req.last_error_type and req.error_shown_ms:
        if all_passed or (failing_case and failing_case[3] != req.last_error_type):
            fix_dur = max(100, int(time.time() * 1000) - req.error_shown_ms)
            cursor.execute(
                """INSERT INTO error_fix (student_id, problem_id, error_type, error_shown_ms, fixed_ms, fix_duration_ms)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (student_id, problem_id, req.last_error_type, req.error_shown_ms, int(time.time() * 1000), fix_dur)
            )
            if fix_dur < 35000:
                award_badge(cursor, student_id, "bug_squasher", "Bug Squasher", "Fixed an error in under 35 seconds!", "⚡")
            conn.commit()

    if all_passed:
        cursor.execute(
            """INSERT INTO attempt (student_id, problem_id, code, status, started_at_ms, submitted_at_ms, duration_ms)
               VALUES (?, ?, ?, 'accepted', ?, ?, ?)""",
            (student_id, problem_id, student_code, req.started_at_ms, req.submitted_at_ms, duration_ms)
        )
        attempt_id = cursor.lastrowid

        now_ms = int(time.time() * 1000)
        cursor.execute(
            """UPDATE problem_session
               SET solved_at_ms = ?, total_time_ms = ?
               WHERE student_id = ? AND problem_id = ?""",
            (now_ms, duration_ms, student_id, problem_id)
        )

        base_xp = 100
        speed_bonus = 50 if duration_ms < 180000 else (25 if duration_ms < 300000 else 0)
        total_xp_earned = base_xp + speed_bonus

        cursor.execute("UPDATE student SET xp = xp + ? WHERE id = ?", (total_xp_earned, student_id))
        cursor.execute("SELECT xp FROM student WHERE id = ?", (student_id,))
        curr_xp = cursor.fetchone()[0]
        new_level = 1 + (curr_xp // 250)
        cursor.execute("UPDATE student SET level = ? WHERE id = ?", (new_level, student_id))

        award_badge(cursor, student_id, "first_solve", "First Solve", "Solved your very first C problem!", "🏆")
        if duration_ms < 120000:
            award_badge(cursor, student_id, "speed_demon", "Speed Solver", "Solved a problem in under 2 minutes!", "🚀")

        cursor.execute("SELECT model_solution, solution_explanation, time_complexity, space_complexity FROM problem WHERE id = ?", (problem_id,))
        sol_row = cursor.fetchone()
        conn.commit()
        conn.close()

        mins = duration_ms // 60000
        secs = (duration_ms % 60000) / 1000.0
        time_display = f"{mins}m {secs:.2f}s" if mins > 0 else f"{secs:.2f}s"

        return {
            "status": "accepted",
            "is_accepted": True,
            "results": results,
            "duration_ms": duration_ms,
            "time_display": time_display,
            "xp_earned": total_xp_earned,
            "new_xp": curr_xp,
            "new_level": new_level,
            "attempt_id": attempt_id,
            "model_solution": sol_row["model_solution"] if sol_row else "",
            "solution_explanation": sol_row["solution_explanation"] if sol_row else "",
            "time_complexity": sol_row["time_complexity"] if sol_row else "O(N)",
            "space_complexity": sol_row["space_complexity"] if sol_row else "O(1)"
        }
    else:
        f_input, f_expected, f_actual, f_stage = failing_case
        divergence = explain_divergence(student_code, problem_id, f_input, f_expected, f_actual)
        detected_error_type = divergence.get("error_type", "wrong_answer")

        cursor.execute(
            """INSERT INTO attempt (student_id, problem_id, code, status, error_type, started_at_ms, submitted_at_ms, duration_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (student_id, problem_id, student_code, f_stage, detected_error_type, req.started_at_ms, req.submitted_at_ms, duration_ms)
        )
        attempt_id = cursor.lastrowid

        auto_create_flashcard(cursor, student_id, detected_error_type, problem_id)
        conn.commit()
        conn.close()

        return {
            "status": f_stage,
            "is_accepted": False,
            "results": results,
            "error_type": detected_error_type,
            "divergence": divergence,
            "attempt_id": attempt_id
        }

def award_badge(cursor, student_id: int, badge_key: str, name: str, desc: str, icon: str):
    cursor.execute("""
        INSERT OR IGNORE INTO student_badge (student_id, badge_key, badge_name, badge_desc, icon)
        VALUES (?, ?, ?, ?, ?)
    """, (student_id, badge_key, name, desc, icon))

def auto_create_flashcard(cursor, student_id: int, mistake_type: str, problem_id: int):
    mistake_map = {
        "off_by_one": (
            "Loop Bounds (0-Indexed vs Size)",
            "for (int i = 0; i <= n; i++) {\n    arr[i] = ...;\n}",
            "In C, array valid indices are 0 to n - 1. Using <= n causes index n (out-of-bounds).",
            "Use 'i < n' instead of 'i <= n' when iterating over size n."
        ),
        "assignment_in_condition": (
            "Assignment (=) vs Equality (==)",
            "if (count = 0) {\n    printf(\"Zero\");\n}",
            "Single '=' assigns 0 to count and evaluates to false. Double '==' performs equality comparison.",
            "Always use 'if (count == 0)' for checks."
        ),
        "sign_error": (
            "Accumulator Sign & Operations",
            "int total = 0;\nfor (int i = 0; i < n; i++) {\n    total -= arr[i]; // Bug\n}",
            "Using subtraction (-=) on an accumulator turns your sum negative.",
            "Use '+=' to accumulate or add elements."
        ),
        "wrong_initial_value": (
            "Finding Extremes with Negative Numbers",
            "int maxVal = 0; // Fails if all arr elements are negative!",
            "If the input array contains [-5, -12, -3], initializing max to 0 returns 0, which is incorrect.",
            "Always initialize maxVal = arr[0] (or INT_MIN from <limits.h>)."
        ),
        "integer_division": (
            "Integer Division Truncation",
            "int a = 7, b = 2;\nfloat res = a / b; // Evaluates to 3.0",
            "Dividing two integers in C discards the decimal fraction before assigning to float.",
            "Cast one operand: '(float)a / b' yields 3.5."
        )
    }

    if mistake_type in mistake_map:
        title, front, concept, fix = mistake_map[mistake_type]
        now_ms = int(time.time() * 1000)
        cursor.execute("""
            INSERT OR IGNORE INTO flashcard (student_id, mistake_type, title, front_code, back_concept, back_fix, box, next_review_ms)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (student_id, mistake_type, title, front, concept, fix, now_ms))

def seed_user_flashcards(cursor, student_id: int):
    now_ms = int(time.time() * 1000)
    defaults = [
        (
            "off_by_one",
            "Array Index Boundaries",
            "int arr[5] = {1, 2, 3, 4, 5};\nint val = arr[5]; // Bug",
            "In C, an array of size 5 has indices 0, 1, 2, 3, 4. Index 5 is out of bounds.",
            "Keep loop conditions as 'i < n' and indices within [0, n-1].",
            1,
            now_ms
        ),
        (
            "pointer_arrow",
            "Struct Pointer (->) vs Dot (.)",
            "struct Node* curr = head;\nint v = curr.val; // Error",
            "When dealing with a pointer to a struct, use the arrow operator '->' instead of dot '.'.",
            "Write 'curr->val' (shorthand for '(*curr).val').",
            1,
            now_ms
        )
    ]
    for mtype, title, fcode, concept, fix, box, rev_ms in defaults:
        cursor.execute("""
            INSERT INTO flashcard (student_id, mistake_type, title, front_code, back_concept, back_fix, box, next_review_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_id, mtype, title, fcode, concept, fix, box, rev_ms))

# ==========================================
# Chatbot & AI Coach Endpoints (relearn_agent.py & chatbot.py)
# ==========================================
@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    # Case A: Simple chat message (e.g. from general AI tutor, modal, or friend's app)
    if req.message and not req.problem_id:
        msg = req.message.strip()
        if not msg:
            raise HTTPException(status_code=400, detail="Message is empty.")
        if msg == "/stats":
            return {
                "reply": f"📊 **Current Tutor Memory Stats**:\n\n- Episodes: {agent.stats().get('episodes', 0)}\n- Facts Learned: {agent.stats().get('facts', 0)}\n- Skills Indexed: {agent.stats().get('skills', 0)}\n- Reflections: {agent.stats().get('reflections', 0)}",
                "stats": agent.stats()
            }
        elif msg == "/reflect":
            reflection = agent.reflect()
            return {"reply": f"💭 **Learning Reflection**:\n\n{reflection}", "stats": agent.stats()}
        elif msg.startswith("/teach "):
            parts = msg[7:].split(" ", 1)
            res = agent.teach(*parts) if len(parts) == 2 else "Usage: /teach key value"
            return {"reply": f"📘 {res}", "stats": agent.stats()}
        
        reply = agent.respond(msg)
        return {"reply": reply, "stats": agent.stats()}

    # Case B: Problem workspace contextual query
    problem_title = ""
    problem_desc = ""
    is_solved = False

    if req.problem_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, description FROM problem WHERE id = ?", (req.problem_id,))
        p_row = cursor.fetchone()
        if p_row:
            problem_title = p_row["title"]
            problem_desc = p_row["description"]
        if req.student_id:
            cursor.execute("SELECT solved_at_ms FROM problem_session WHERE student_id = ? AND problem_id = ?", (req.student_id, req.problem_id))
            sess = cursor.fetchone()
            if sess and sess["solved_at_ms"]:
                is_solved = True
        conn.close()

    query_text = req.prompt or req.message or ""
    if problem_title or req.code:
        reply = agent.coach(
            mode="chat",
            problem=f"{problem_title}\n{problem_desc}",
            code=req.code or "",
            output=json.dumps(req.error_info or {}),
            question=query_text
        )
    else:
        reply = agent.respond(query_text)

    return {"reply": reply, "stats": agent.stats()}

@app.post("/api/coach")
def coach_endpoint(req: CoachRequest):
    problem_text = req.problem
    if req.problem_id and not problem_text:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT title, description FROM problem WHERE id = ?", (req.problem_id,))
            p_row = cursor.fetchone()
            if p_row:
                problem_text = f"{p_row['title']}\n{p_row['description']}"
            conn.close()
        except Exception:
            pass

    reply = agent.coach(
        mode=req.mode or "chat",
        problem=problem_text or "",
        code=req.code or "",
        output=req.output or "",
        question=req.question or ""
    )
    return {"reply": reply, "stats": agent.stats()}

@app.get("/api/stats")
def stats_endpoint():
    return {
        "stats": agent.stats(),
        "model": agent.model,
        "configured": agent.client is not None,
        "facts": agent.memory.get_all_facts(),
    }

@app.post("/api/reflect")
def reflect_endpoint():
    return {
        "reflection": agent.reflect(),
        "stats": agent.stats()
    }

@app.post("/api/teach")
def teach_endpoint(req: TeachRequest):
    key = req.key.strip()
    val = req.value.strip()
    if not key or not val:
        raise HTTPException(status_code=400, detail="Key and value are required.")
    return {
        "result": agent.teach(key, val),
        "stats": agent.stats()
    }

# Backward-compatibility aliases
@app.post("/api/agent/chat")
def agent_chat_endpoint(req: AgentChatRequest):
    return chat_endpoint(ChatRequest(message=req.message, student_id=req.student_id))

@app.post("/api/agent/reflect")
def agent_reflect_endpoint():
    return reflect_endpoint()

@app.get("/api/agent/stats")
def agent_stats_endpoint():
    return stats_endpoint()

# ==========================================
# Progress & Analytics Endpoint
# ==========================================
@app.get("/api/progress")
def get_student_progress(student_id: int = Query(...)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(DISTINCT problem_id) FROM problem_session WHERE student_id = ? AND solved_at_ms IS NOT NULL", (student_id,))
    solved_count = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM attempt WHERE student_id = ? GROUP BY status", (student_id,))
    status_counts = dict(cursor.fetchall())
    total_attempts = sum(status_counts.values())
    accepted_attempts = status_counts.get("accepted", 0)
    accuracy_pct = round((accepted_attempts / total_attempts * 100), 1) if total_attempts > 0 else 0

    cursor.execute("""
        SELECT p.id, p.title, p.topic, ps.total_time_ms
        FROM problem_session ps
        JOIN problem p ON ps.problem_id = p.id
        WHERE ps.student_id = ? AND ps.solved_at_ms IS NOT NULL
        ORDER BY ps.solved_at_ms ASC
    """, (student_id,))
    solve_times = [dict(row) for row in cursor.fetchall()]

    cursor.execute("""
        SELECT error_type, COUNT(*) as cnt
        FROM attempt
        WHERE student_id = ? AND error_type IS NOT NULL AND status != 'accepted'
        GROUP BY error_type
        ORDER BY cnt DESC
    """, (student_id,))
    error_types = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT AVG(fix_duration_ms), COUNT(*) FROM error_fix WHERE student_id = ?", (student_id,))
    avg_fix_row = cursor.fetchone()
    avg_fix_ms = int(avg_fix_row[0]) if avg_fix_row[0] is not None else 0
    total_fixes = avg_fix_row[1]

    cursor.execute("""
        SELECT p.topic, COUNT(DISTINCT p.id) as total_in_topic,
               COUNT(DISTINCT ps.problem_id) as solved_in_topic
        FROM problem p
        LEFT JOIN problem_session ps ON p.id = ps.problem_id AND ps.student_id = ? AND ps.solved_at_ms IS NOT NULL
        GROUP BY p.topic
    """, (student_id,))
    topic_mastery = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return {
        "solved_count": solved_count,
        "total_attempts": total_attempts,
        "accuracy_pct": accuracy_pct,
        "solve_times": solve_times,
        "error_types": error_types,
        "avg_fix_ms": avg_fix_ms,
        "total_fixes": total_fixes,
        "topic_mastery": topic_mastery
    }

# ==========================================
# Flashcards API
# ==========================================
@app.get("/api/flashcards")
def get_flashcards(student_id: int = Query(...)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, mistake_type, title, front_code, back_concept, back_fix, box, next_review_ms
        FROM flashcard
        WHERE student_id = ?
        ORDER BY next_review_ms ASC, id ASC
    """, (student_id,))
    cards = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"cards": cards}

@app.post("/api/flashcards/{card_id}/review")
def review_flashcard(card_id: int, req: CardReviewRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT box FROM flashcard WHERE id = ? AND student_id = ?", (card_id, req.student_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Flashcard not found.")

    curr_box = row["box"] or 1
    now_ms = int(time.time() * 1000)

    if req.rating == "got_it":
        new_box = min(5, curr_box + 1)
        intervals = {1: 86400000, 2: 259200000, 3: 604800000, 4: 1209600000, 5: 2592000000}
        next_review_ms = now_ms + intervals.get(new_box, 86400000)
    else:
        new_box = 1
        next_review_ms = now_ms + 600000

    cursor.execute(
        "UPDATE flashcard SET box = ?, next_review_ms = ? WHERE id = ?",
        (new_box, next_review_ms, card_id)
    )
    conn.commit()
    conn.close()

    return {"ok": True, "new_box": new_box, "next_review_ms": next_review_ms}

# ==========================================
# HTML Page Routes
# ==========================================
@app.get("/")
def serve_home():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/signup")
def serve_signup():
    return FileResponse(STATIC_DIR / "signup.html")

@app.get("/login")
def serve_login():
    return FileResponse(STATIC_DIR / "login.html")

@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")

@app.get("/problems")
def serve_problems():
    return FileResponse(STATIC_DIR / "problems.html")

@app.get("/problems/{problem_id}")
def serve_problem_detail(problem_id: int):
    return FileResponse(STATIC_DIR / "problem_detail.html")

@app.get("/progress")
def serve_progress():
    return FileResponse(STATIC_DIR / "progress.html")

@app.get("/cards")
def serve_cards():
    return FileResponse(STATIC_DIR / "cards.html")

@app.get("/practice")
def redirect_practice():
    return FileResponse(STATIC_DIR / "problems.html")

# Static Assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

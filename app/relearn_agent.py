import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# ============================================================
# MEMORY STORE
# ============================================================

class MemoryStore:
    """Persistent memory system for ReLearn."""

    def __init__(self, storage_path: str = "relearn_memory.json"):
        self.storage_path = storage_path
        self.memory = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"episodic": [], "semantic": {}, "skills": {}, "reflections": []}

    def _save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, indent=2, ensure_ascii=False, default=str)

    def add_episode(self, user_input: str, agent_output: str, metadata: Dict = None):
        episode = {
            "id": hashlib.md5(f"{user_input}{datetime.now()}".encode()).hexdigest()[:8],
            "timestamp": datetime.now().isoformat(),
            "input": user_input,
            "output": agent_output,
            "metadata": metadata or {},
        }
        self.memory["episodic"].append(episode)
        self._save()
        return episode["id"]

    def add_fact(self, key: str, value: Any, source: str = "interaction"):
        self.memory["semantic"][key] = {
            "value": value,
            "source": source,
            "learned_at": datetime.now().isoformat(),
        }
        self._save()

    def add_skill(self, name: str, description: str, procedure: List[str]):
        self.memory["skills"][name] = {
            "description": description,
            "procedure": procedure,
            "created_at": datetime.now().isoformat(),
            "usage_count": 0,
        }
        self._save()

    def add_reflection(self, reflection: str, context: str):
        self.memory["reflections"].append({
            "reflection": reflection,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        })
        self._save()

    def recall_relevant(self, query: str, top_k: int = 5) -> List[Dict]:
        query_words = set(query.lower().split())
        scored = []
        for ep in self.memory["episodic"]:
            text = (ep["input"] + " " + ep["output"]).lower()
            overlap = len(query_words & set(text.split()))
            if overlap > 0:
                scored.append((overlap, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:top_k]]

    def get_all_facts(self) -> Dict:
        return self.memory["semantic"]

    def get_stats(self) -> Dict:
        return {
            "episodes": len(self.memory["episodic"]),
            "facts": len(self.memory["semantic"]),
            "skills": len(self.memory["skills"]),
            "reflections": len(self.memory["reflections"]),
        }


# ============================================================
# RELEARN AGENT
# ============================================================

class ReLearnAgent:
    """ReLearn AI Agent: answers, remembers, learns facts/skills, reflects."""

    def __init__(
        self,
        name: str = "ReLearn",
        llm_provider: str = "openai",
        api_key: Optional[str] = None,
        model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        memory_path: str = "relearn_memory.json",
    ):
        self.name = name
        self.model = model
        self.llm_provider = llm_provider
        self.memory = MemoryStore(memory_path)
        self.conversation_history = []
        self.client = None

        # Gemini through OpenAI-compatible endpoint
        if llm_provider == "openai" and OpenAI is not None:
            key = api_key or os.getenv("GEMINI_API_KEY")
            if not key:
                try:
                    from app.chatbot import get_gemini_api_key
                    key = get_gemini_api_key()
                except Exception:
                    pass
            if key:
                self.client = OpenAI(
                    api_key=key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                )

    # ---------------- SYSTEM PROMPT ----------------

    def _build_system_prompt(self) -> str:
        stats = self.memory.get_stats()
        facts = self.memory.get_all_facts()
        facts_summary = "\n".join(
            f"- {k}: {v['value']}" for k, v in list(facts.items())[:20]
        ) or "No facts learned yet."

        return f"""
You are {self.name}, an adaptive AI learning agent for the ReLearn project.

Your main purpose is to help students learn programming,
especially introductory C programming.

IMPORTANT BEHAVIOR:
1. Understand the student's question.
2. Give a simple explanation.
3. If the student provides code, identify the error.
4. Explain WHY the error occurs.
5. Show the corrected code when appropriate.
6. Use examples suitable for beginners.
7. Remember useful information from previous interactions.
8. Use previous mistakes to personalize future explanations.
9. Do not pretend to remember information that is not available.
10. If uncertain, clearly say so.

For programming questions:
- Identify the misconception.
- Explain the concept.
- Show the mistake.
- Show the correction.
- Give a small example.
- Ask a short follow-up question when useful.

Current memory statistics:
Episodes: {stats['episodes']}
Facts: {stats['facts']}
Skills: {stats['skills']}
Reflections: {stats['reflections']}

Known facts:
{facts_summary}
"""

    # ---------------- RULE-BASED FALLBACK ----------------

    def _fallback_c_response(self, user_input: str) -> str:
        q = user_input.lower()
        if "mode: hint" in q or "give me a hint" in q:
            return (
                "💡 **Coaching Hint**:\n\n"
                "1. Break the problem into small steps (e.g. initialization, iteration condition, pointer updates).\n"
                "2. Trace your logic with a small input on paper (e.g. `[1, 2, 3]`).\n"
                "3. Pay close attention to edge cases like empty inputs, `NULL` pointers, and single-element bounds."
            )
        elif "mode: error" in q or "explain my error" in q:
            return (
                "🔍 **Error Analysis Guidance**:\n\n"
                "Review the compiler output or failing test case carefully:\n"
                "- **Semicolon or Syntax Error**: Check the flagged line and the line directly above it for missing `;` or unbalanced brackets `{}`.\n"
                "- **Off-by-one**: Check if your loop condition is `< n` instead of `<= n`.\n"
                "- **Segfault**: Ensure you aren't accessing `NULL` pointers or array indices `< 0` or `>= n`."
            )
        elif "mode: problem" in q or "explain this problem" in q:
            return (
                "📖 **Problem Overview**:\n\n"
                "Review the inputs and required return value.\n"
                "- Focus on what state needs to be maintained across each iteration.\n"
                "- Make sure your algorithm handles edge cases like `NULL` pointers or negative integers."
            )
        elif "pointer" in q:
            return (
                "💡 **Understanding Pointers in C**:\n\n"
                "A pointer is simply a variable that stores the **memory address** of another variable.\n\n"
                "- Declaration: `int *ptr;` creates a pointer to an integer.\n"
                "- Address-of (`&`): `ptr = &x;` stores the address of `x` in `ptr`.\n"
                "- Dereference (`*`): `*ptr = 10;` changes the value at that address.\n\n"
                "⚠️ **Common Mistake**: Dereferencing an uninitialized or `NULL` pointer causes a **Segmentation Fault**."
            )
        elif "segfault" in q or "segmentation" in q:
            return (
                "🔍 **Why Segmentation Faults Occur**:\n\n"
                "A segmentation fault happens when your program tries to read or write memory it doesn't have permission to access.\n\n"
                "**Top 3 Causes in C**:\n"
                "1. **Dereferencing NULL**: Accessing `*ptr` when `ptr == NULL`.\n"
                "2. **Out of bounds array access**: Reading `arr[n]` when valid indices are `0` to `n-1`.\n"
                "3. **Using freed memory**: Reading a pointer after calling `free(ptr)`."
            )
        elif "linked list" in q or "list" in q:
            return (
                "🔗 **Linked Lists vs Arrays in C**:\n\n"
                "- **Arrays**: Contiguous memory blocks with fast $O(1)$ random indexing (`arr[i]`), but fixed size.\n"
                "- **Linked Lists**: Independent nodes scattered in memory connected via `next` pointers. Insertion and deletion can be $O(1)$ without shifting elements.\n\n"
                "```c\nstruct Node {\n    int val;\n    struct Node *next;\n};\n```"
            )
        elif "malloc" in q or "free" in q or "heap" in q:
            return (
                "📦 **Dynamic Memory Allocation in C (`malloc` / `free`)**:\n\n"
                "- `malloc(size)` allocates uninitialized memory on the **heap** and returns a `void*`.\n"
                "- Always check if the pointer is `NULL` before using it!\n"
                "- Every `malloc` must have a matching `free` to prevent **memory leaks**.\n\n"
                "```c\nint *arr = (int*)malloc(n * sizeof(int));\nif (arr == NULL) { /* handle error */ }\n// ... use arr ...\nfree(arr);\n```"
            )
        elif "array" in q:
            return (
                "📊 **Arrays in C**:\n\n"
                "In C, arrays are zero-indexed (`0` to `n - 1`). The array variable itself decays to a pointer to its first element (`arr == &arr[0]`).\n\n"
                "⚠️ Remember: C does not perform automatic bounds checking. Accessing `arr[n]` leads to undefined behavior!"
            )
        return (
            "🤖 **Re:Learn AI Tutor**:\n\n"
            "I'm here to help you understand C programming concepts like pointers, memory layout, arrays, linked lists, and debugging errors.\n\n"
            "Feel free to ask a specific question or paste a snippet of C code that you'd like me to explain or debug!"
        )

    # ---------------- LLM CALL ----------------

    def _call_llm(self, messages: List[Dict]) -> str:
        if self.client is None:
            # Extract last user message
            last_msg = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_msg = m.get("content", "")
                    break
            return self._fallback_c_response(last_msg)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1200,
            )
            return response.choices[0].message.content or "No response generated."
        except Exception as e:
            # Fallback on API failure
            last_msg = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_msg = m.get("content", "")
                    break
            return self._fallback_c_response(last_msg)

    # ---------------- LEARNING EXTRACTION ----------------

    def _extract_learnings(self, user_input: str, response: str) -> Dict:
        extraction_prompt = f"""
Analyze this student interaction.

USER:
{user_input}

AGENT:
{response}

Extract useful learning information.

Return ONLY valid JSON:

{{
    "facts": {{"key": "value"}},
    "skill": null,
    "reflection": "short reflection"
}}

If there is no useful fact or skill, return empty values.
"""
        messages = [
            {"role": "system",
             "content": "You extract structured learning information. Return ONLY valid JSON."},
            {"role": "user", "content": extraction_prompt},
        ]
        result = self._call_llm(messages)
        try:
            result = result.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(result)
        except Exception:
            return {"facts": {}, "skill": None, "reflection": ""}

    # ---------------- MAIN RESPONSE ----------------

    def respond(self, user_input: str, auto_learn: bool = True) -> str:
        relevant_past = self.memory.recall_relevant(user_input, top_k=3)

        context_note = ""
        if relevant_past:
            context_note = "\n\nRelevant previous interactions:\n"
            for ep in relevant_past:
                context_note += f"- Question: {ep['input'][:150]}\n"
                context_note += f"  Answer: {ep['output'][:200]}\n"

        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(self.conversation_history[-10:])
        messages.append({"role": "user", "content": user_input + context_note})

        response = self._call_llm(messages)

        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response})

        if auto_learn:
            learnings = self._extract_learnings(user_input, response)

            for key, value in learnings.get("facts", {}).items():
                self.memory.add_fact(key, value, source="auto_extraction")

            skill = learnings.get("skill")
            if skill and isinstance(skill, dict) and skill.get("name"):
                self.memory.add_skill(
                    skill["name"],
                    skill.get("description", ""),
                    skill.get("steps", []),
                )

            reflection = learnings.get("reflection", "")
            if reflection:
                self.memory.add_reflection(reflection, context=user_input[:200])

        self.memory.add_episode(user_input, response)
        return response

    # ---------------- C COACH ----------------

    def coach(self, mode: str = "chat", problem: str = "", code: str = "",
              output: str = "", question: str = "") -> str:
        rules = {
            "hint": "Give ONE short hint (max 3 sentences). Do NOT reveal the full solution or write the full code.",
            "error": "Explain the error or failing output in simple words. Name the likely misconception, point to the line, and suggest what to check. Do NOT give the full solution.",
            "problem": "Explain the problem in simple words with one tiny example. Do NOT write solution code.",
            "chat": "Answer as a friendly C practice coach. Prefer guiding questions over full solutions.",
        }
        prompt = f"""MODE: {mode}
INSTRUCTION: {rules.get(mode, rules['chat'])}

PROBLEM:
{problem[:1500]}

STUDENT CODE:
{code[:3000]}

TEST OUTPUT / ERROR:
{output[:1500]}

STUDENT QUESTION:
{question or '(none)'}
"""
        messages = [{"role": "system", "content": self._build_system_prompt()}]
        messages.extend(self.conversation_history[-6:])
        messages.append({"role": "user", "content": prompt})

        reply = self._call_llm(messages)

        self.conversation_history.append({"role": "user", "content": question or f"[{mode}]"})
        self.conversation_history.append({"role": "assistant", "content": reply})
        self.memory.add_episode(question or f"[{mode}] {problem[:80]}", reply, {"mode": mode})
        return reply

    # ---------------- REFLECTION ----------------

    def reflect(self) -> str:
        stats = self.memory.get_stats()
        recent_episodes = self.memory.memory["episodic"][-10:]
        summary = "\n".join(f"- {ep['input'][:100]}" for ep in recent_episodes)

        prompt = f"""
Reflect on the student's recent learning.

Stats:
{json.dumps(stats)}

Recent interactions:
{summary}

Identify:
1. Common mistakes
2. Concepts the student struggles with
3. What the agent learned
4. How future explanations should improve

Keep it under 200 words.
"""
        return self._call_llm([
            {"role": "system", "content": "You are a reflective educational AI."},
            {"role": "user", "content": prompt},
        ])

    # ---------------- TEACH / STATS ----------------

    def teach(self, fact_key: str, fact_value: str):
        self.memory.add_fact(fact_key, fact_value, source="explicit_teaching")
        return f"Learned: {fact_key} = {fact_value}"

    def stats(self):
        return self.memory.get_stats()


# ============================================================
# TERMINAL MODE (optional)
# ============================================================

def main():
    agent = ReLearnAgent()
    print(f"🤖 {agent.name} initialized. Model: {agent.model}")
    print("Commands: /reflect, /stats, /teach <key> <value>, /quit\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except KeyboardInterrupt:
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input == "/quit":
            break
        if user_input == "/stats":
            print(f"📊 {agent.stats()}\n")
            continue
        if user_input == "/reflect":
            print(f"\n💭 {agent.reflect()}\n")
            continue
        if user_input.startswith("/teach "):
            parts = user_input[7:].split(" ", 1)
            print(agent.teach(*parts) if len(parts) == 2 else "Usage: /teach key value")
            continue

        print("\n🤔 ReLearn is thinking...\n")
        print(f"ReLearn: {agent.respond(user_input)}\n")


if __name__ == "__main__":
    main()

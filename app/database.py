import sqlite3
import time
import os
from pathlib import Path

if os.getenv("VERCEL"):
    DB_FILE = Path("/tmp/relearn.db")
else:
    DB_FILE = Path(__file__).resolve().parent.parent / "relearn.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Student table with gamification attributes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 1,
        streak INTEGER DEFAULT 1,
        last_active_date TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Migrate columns if student table existed previously without them
    cursor.execute("PRAGMA table_info(student);")
    cols = [row[1] for row in cursor.fetchall()]
    if "xp" not in cols:
        cursor.execute("ALTER TABLE student ADD COLUMN xp INTEGER DEFAULT 0;")
    if "level" not in cols:
        cursor.execute("ALTER TABLE student ADD COLUMN level INTEGER DEFAULT 1;")
    if "streak" not in cols:
        cursor.execute("ALTER TABLE student ADD COLUMN streak INTEGER DEFAULT 1;")
    if "last_active_date" not in cols:
        cursor.execute("ALTER TABLE student ADD COLUMN last_active_date TEXT;")

    # 2. Problem table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS problem (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        description TEXT NOT NULL,
        starter_code TEXT NOT NULL,
        model_solution TEXT NOT NULL,
        solution_explanation TEXT NOT NULL,
        time_complexity TEXT,
        space_complexity TEXT
    );
    """)

    # 3. Test Cases table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_case (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problem_id INTEGER NOT NULL,
        input TEXT NOT NULL,
        expected_output TEXT NOT NULL,
        is_hidden INTEGER DEFAULT 0,
        FOREIGN KEY (problem_id) REFERENCES problem(id) ON DELETE CASCADE
    );
    """)

    # 4. Attempt table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attempt (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        problem_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        status TEXT NOT NULL,
        error_line INTEGER,
        error_type TEXT,
        started_at_ms INTEGER NOT NULL,
        submitted_at_ms INTEGER NOT NULL,
        duration_ms INTEGER NOT NULL,
        FOREIGN KEY (student_id) REFERENCES student(id),
        FOREIGN KEY (problem_id) REFERENCES problem(id)
    );
    """)

    # 5. Problem Session table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS problem_session (
        student_id INTEGER NOT NULL,
        problem_id INTEGER NOT NULL,
        first_opened_ms INTEGER NOT NULL,
        solved_at_ms INTEGER,
        total_time_ms INTEGER DEFAULT 0,
        PRIMARY KEY (student_id, problem_id),
        FOREIGN KEY (student_id) REFERENCES student(id),
        FOREIGN KEY (problem_id) REFERENCES problem(id)
    );
    """)

    # 6. Error Fix tracking table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS error_fix (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id INTEGER,
        student_id INTEGER NOT NULL,
        problem_id INTEGER NOT NULL,
        error_type TEXT NOT NULL,
        error_shown_ms INTEGER NOT NULL,
        fixed_ms INTEGER NOT NULL,
        fix_duration_ms INTEGER NOT NULL,
        FOREIGN KEY (attempt_id) REFERENCES attempt(id),
        FOREIGN KEY (student_id) REFERENCES student(id),
        FOREIGN KEY (problem_id) REFERENCES problem(id)
    );
    """)

    # 7. Student Badges
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_badge (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        badge_key TEXT NOT NULL,
        badge_name TEXT NOT NULL,
        badge_desc TEXT NOT NULL,
        icon TEXT NOT NULL,
        awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(student_id, badge_key),
        FOREIGN KEY (student_id) REFERENCES student(id)
    );
    """)

    # 8. Flashcards
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcard (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        mistake_type TEXT NOT NULL,
        title TEXT NOT NULL,
        front_code TEXT NOT NULL,
        back_concept TEXT NOT NULL,
        back_fix TEXT NOT NULL,
        box INTEGER DEFAULT 1,
        next_review_ms INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES student(id)
    );
    """)

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM problem")
    if cursor.fetchone()[0] == 0:
        seed_problems(cursor)
        conn.commit()

    conn.close()

def seed_problems(cursor):
    problems_data = [
        (
            1,
            "Find Maximum in Array",
            "Arrays",
            "Easy",
            """Given an array of integers <code>arr</code> and its length <code>n</code> (where <code>n >= 1</code>), write a C function to find and return the maximum value in the array.

<h3>Function Signature</h3>
<pre><code>int findMax(int arr[], int n);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: arr = [3, 7, 2, 9, 5], n = 5
Output: 9</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: arr = [-10, -3, -50], n = 3
Output: -3</pre>

<h3>Constraints</h3>
<ul>
  <li><code>1 <= n <= 1000</code></li>
  <li><code>-10000 <= arr[i] <= 10000</code></li>
</ul>""",
            """// Return the maximum element in the array
int findMax(int arr[], int n) {
    // Your code here
    
}""",
            """int findMax(int arr[], int n) {
    int maxVal = arr[0];
    for (int i = 1; i < n; i++) {
        if (arr[i] > maxVal) {
            maxVal = arr[i];
        }
    }
    return maxVal;
}""",
            """To find the maximum element, initialize <code>maxVal</code> to the first element (<code>arr[0]</code>). Then iterate through the array from index <code>1</code> to <code>n - 1</code>. If any element <code>arr[i]</code> is strictly greater than <code>maxVal</code>, update <code>maxVal = arr[i]</code>. Finally, return <code>maxVal</code>. Initializing with <code>arr[0]</code> handles negative numbers properly, avoiding bugs from initializing to <code>0</code>.""",
            "O(N)",
            "O(1)"
        ),
        (
            2,
            "Sum of Array Elements",
            "Arrays",
            "Easy",
            """Given an array of integers <code>arr</code> and its size <code>n</code>, calculate and return the sum of all elements in the array.

<h3>Function Signature</h3>
<pre><code>int sumArray(int arr[], int n);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: arr = [1, 2, 3, 4, 5], n = 5
Output: 15</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: arr = [10, -2, 5], n = 3
Output: 13</pre>

<h3>Constraints</h3>
<ul>
  <li><code>0 <= n <= 1000</code></li>
  <li>If <code>n == 0</code>, return <code>0</code>.</li>
</ul>""",
            """// Return the sum of all elements in arr
int sumArray(int arr[], int n) {
    // Your code here
    
}""",
            """int sumArray(int arr[], int n) {
    int sum = 0;
    for (int i = 0; i < n; i++) {
        sum += arr[i];
    }
    return sum;
}""",
            """Initialize an accumulator variable <code>sum = 0</code>. Loop through each index <code>i</code> from <code>0</code> to <code>n - 1</code> and add <code>arr[i]</code> to <code>sum</code>. Return <code>sum</code> after the loop terminates.""",
            "O(N)",
            "O(1)"
        ),
        (
            3,
            "Reverse Array In-Place",
            "Arrays",
            "Easy",
            """Given an array of integers <code>arr</code> and its length <code>n</code>, reverse the elements in-place (modify the array directly).

<h3>Function Signature</h3>
<pre><code>void reverseArray(int arr[], int n);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: arr = [1, 2, 3, 4], n = 4
Output: [4, 3, 2, 1]</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: arr = [5], n = 1
Output: [5]</pre>

<h3>Constraints</h3>
<ul>
  <li><code>0 <= n <= 1000</code></li>
  <li>Must modify <code>arr</code> in-place with <code>O(1)</code> extra space.</li>
</ul>""",
            """// Reverse the array elements in-place
void reverseArray(int arr[], int n) {
    // Your code here
    
}""",
            """void reverseArray(int arr[], int n) {
    int left = 0;
    int right = n - 1;
    while (left < right) {
        int temp = arr[left];
        arr[left] = arr[right];
        arr[right] = temp;
        left++;
        right--;
    }
}""",
            """Use the two-pointer technique. Point <code>left</code> at index <code>0</code> and <code>right</code> at index <code>n - 1</code>. While <code>left < right</code>, swap <code>arr[left]</code> and <code>arr[right]</code> using a temporary variable, increment <code>left</code>, and decrement <code>right</code>.""",
            "O(N)",
            "O(1)"
        ),
        (
            4,
            "Second Largest Element",
            "Arrays",
            "Medium",
            """Given an array of integers <code>arr</code> and its length <code>n</code>, return the second strictly largest element in the array. If no second distinct largest element exists, return <code>-1</code>.

<h3>Function Signature</h3>
<pre><code>int secondLargest(int arr[], int n);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: arr = [12, 35, 1, 10, 34, 1], n = 6
Output: 34</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: arr = [10, 10, 10], n = 3
Output: -1</pre>

<h3>Constraints</h3>
<ul>
  <li><code>1 <= n <= 1000</code></li>
  <li><code>0 <= arr[i] <= 100000</code></li>
</ul>""",
            """// Return second distinct largest or -1 if none exists
int secondLargest(int arr[], int n) {
    // Your code here
    
}""",
            """int secondLargest(int arr[], int n) {
    if (n < 2) return -1;
    int first = -1;
    int second = -1;
    for (int i = 0; i < n; i++) {
        if (arr[i] > first) {
            second = first;
            first = arr[i];
        } else if (arr[i] > second && arr[i] != first) {
            second = arr[i];
        }
    }
    return second;
}""",
            """Maintain two variables: <code>first</code> (largest) and <code>second</code> (second largest), initialized to <code>-1</code>. Traverse the array once: if the current element is greater than <code>first</code>, update <code>second = first</code> and <code>first = arr[i]</code>. Otherwise, if it is greater than <code>second</code> and not equal to <code>first</code>, update <code>second = arr[i]</code>.""",
            "O(N)",
            "O(1)"
        ),
        (
            5,
            "Count Occurrences",
            "Arrays",
            "Easy",
            """Given an array of integers <code>arr</code>, length <code>n</code>, and a target value <code>target</code>, return how many times <code>target</code> appears in <code>arr</code>.

<h3>Function Signature</h3>
<pre><code>int countOccurrences(int arr[], int n, int target);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: arr = [1, 2, 2, 3, 2, 4], n = 6, target = 2
Output: 3</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: arr = [5, 9, 12], n = 3, target = 7
Output: 0</pre>""",
            """// Count frequency of target in arr
int countOccurrences(int arr[], int n, int target) {
    // Your code here
    
}""",
            """int countOccurrences(int arr[], int n, int target) {
    int count = 0;
    for (int i = 0; i < n; i++) {
        if (arr[i] == target) {
            count++;
        }
    }
    return count;
}""",
            """Initialize a counter <code>count = 0</code>. Loop through the array and check each element with the equality comparison operator <code>arr[i] == target</code>. If equal, increment <code>count</code>. Return <code>count</code>.""",
            "O(N)",
            "O(1)"
        ),
        (
            6,
            "Sum Linked List Values",
            "Linked List",
            "Easy",
            """Given the head pointer to a singly linked list of integers, calculate and return the sum of all node values.

<h3>Node Definition</h3>
<pre><code>struct Node {
    int val;
    struct Node* next;
};</code></pre>

<h3>Function Signature</h3>
<pre><code>int sumList(struct Node* head);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: 1 -> 2 -> 3 -> 4 -> NULL
Output: 10</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: NULL (empty list)
Output: 0</pre>""",
            """/*
struct Node {
    int val;
    struct Node* next;
};
*/
int sumList(struct Node* head) {
    // Your code here
    
}""",
            """int sumList(struct Node* head) {
    int total = 0;
    struct Node* curr = head;
    while (curr != NULL) {
        total += curr->val;
        curr = curr->next;
    }
    return total;
}""",
            """Iterate through the list using a pointer <code>curr = head</code>. While <code>curr != NULL</code>, add <code>curr->val</code> to <code>total</code> and advance <code>curr = curr->next</code>. Return <code>total</code>.""",
            "O(N)",
            "O(1)"
        ),
        (
            7,
            "Reverse a Linked List",
            "Linked List",
            "Medium",
            """Given the head of a singly linked list, reverse the list pointers in-place and return the new head pointer.

<h3>Node Definition</h3>
<pre><code>struct Node {
    int val;
    struct Node* next;
};</code></pre>

<h3>Function Signature</h3>
<pre><code>struct Node* reverseList(struct Node* head);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: 1 -> 2 -> 3 -> NULL
Output: 3 -> 2 -> 1 -> NULL</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: 42 -> NULL
Output: 42 -> NULL</pre>""",
            """/*
struct Node {
    int val;
    struct Node* next;
};
*/
struct Node* reverseList(struct Node* head) {
    // Your code here
    
}""",
            """struct Node* reverseList(struct Node* head) {
    struct Node* prev = NULL;
    struct Node* curr = head;
    while (curr != NULL) {
        struct Node* nextNode = curr->next;
        curr->next = prev;
        prev = curr;
        curr = nextNode;
    }
    return prev;
}""",
            """Use three pointers: <code>prev</code> (initially NULL), <code>curr</code> (head), and <code>nextNode</code>. In each step of the loop, save <code>nextNode = curr->next</code>, redirect <code>curr->next = prev</code>, advance <code>prev = curr</code>, and move <code>curr = nextNode</code>. When <code>curr</code> becomes NULL, <code>prev</code> points to the new head.""",
            "O(N)",
            "O(1)"
        ),
        (
            8,
            "Find Middle Node Value",
            "Linked List",
            "Easy",
            """Given a singly linked list, return the value of the middle node. If there are two middle nodes (even length), return the second middle node's value.

<h3>Node Definition</h3>
<pre><code>struct Node {
    int val;
    struct Node* next;
};</code></pre>

<h3>Function Signature</h3>
<pre><code>int findMiddle(struct Node* head);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: 1 -> 2 -> 3 -> 4 -> 5 -> NULL
Output: 3</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: 10 -> 20 -> 30 -> 40 -> NULL
Output: 30</pre>""",
            """/*
struct Node {
    int val;
    struct Node* next;
};
*/
int findMiddle(struct Node* head) {
    // Your code here
    
}""",
            """int findMiddle(struct Node* head) {
    if (head == NULL) return 0;
    struct Node* slow = head;
    struct Node* fast = head;
    while (fast != NULL && fast->next != NULL) {
        slow = slow->next;
        fast = fast->next->next;
    }
    return slow->val;
}""",
            """Use the fast & slow pointer technique (Tortoise and Hare). Both start at <code>head</code>. Advance <code>slow</code> by 1 node (<code>slow->next</code>) and <code>fast</code> by 2 nodes (<code>fast->next->next</code>) per iteration. When <code>fast</code> reaches the end or NULL, <code>slow</code> will be located precisely at the middle node.""",
            "O(N)",
            "O(1)"
        ),
        (
            9,
            "Count Nodes in List",
            "Linked List",
            "Easy",
            """Given the head of a singly linked list, count and return the total number of nodes in the list.

<h3>Node Definition</h3>
<pre><code>struct Node {
    int val;
    struct Node* next;
};</code></pre>

<h3>Function Signature</h3>
<pre><code>int countNodes(struct Node* head);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: 10 -> 20 -> 30 -> NULL
Output: 3</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: NULL
Output: 0</pre>""",
            """/*
struct Node {
    int val;
    struct Node* next;
};
*/
int countNodes(struct Node* head) {
    // Your code here
    
}""",
            """int countNodes(struct Node* head) {
    int count = 0;
    struct Node* curr = head;
    while (curr != NULL) {
        count++;
        curr = curr->next;
    }
    return count;
}""",
            """Initialize a counter <code>count = 0</code>. Traverse from <code>head</code> to the end using <code>curr = curr->next</code>, incrementing <code>count</code> at each node. Return <code>count</code>.""",
            "O(N)",
            "O(1)"
        ),
        (
            10,
            "Detect Value in List",
            "Linked List",
            "Easy",
            """Given the head of a singly linked list and a target integer <code>target</code>, return <code>1</code> if <code>target</code> is present in the list, or <code>0</code> otherwise.

<h3>Function Signature</h3>
<pre><code>int detectValue(struct Node* head, int target);</code></pre>

<h3>Examples</h3>
<p><strong>Example 1:</strong></p>
<pre>Input: 5 -> 15 -> 25 -> NULL, target = 15
Output: 1</pre>

<p><strong>Example 2:</strong></p>
<pre>Input: 1 -> 2 -> 3 -> NULL, target = 99
Output: 0</pre>""",
            """/*
struct Node {
    int val;
    struct Node* next;
};
*/
int detectValue(struct Node* head, int target) {
    // Your code here
    
}""",
            """int detectValue(struct Node* head, int target) {
    struct Node* curr = head;
    while (curr != NULL) {
        if (curr->val == target) {
            return 1;
        }
        curr = curr->next;
    }
    return 0;
}""",
            """Traverse the linked list node by node. If <code>curr->val == target</code>, immediately return <code>1</code>. If the loop completes without finding the target (<code>curr == NULL</code>), return <code>0</code>.""",
            "O(N)",
            "O(1)"
        )
    ]

    cursor.executemany("""
    INSERT INTO problem (id, title, topic, difficulty, description, starter_code, model_solution, solution_explanation, time_complexity, space_complexity)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, problems_data)

    test_cases_data = [
        # Problem 1: Find Max (5 test cases: 3 public, 2 hidden)
        (1, "5\n3 7 2 9 5", "9", 0),
        (1, "3\n-10 -3 -50", "-3", 0),
        (1, "1\n42", "42", 0),
        (1, "6\n100 200 50 400 300 250", "400", 1),
        (1, "4\n-1 -5 -2 -8", "-1", 1),

        # Problem 2: Sum Array (4 test cases)
        (2, "5\n1 2 3 4 5", "15", 0),
        (2, "3\n10 -2 5", "13", 0),
        (2, "0\n", "0", 0),
        (2, "4\n100 200 300 400", "1000", 1),

        # Problem 3: Reverse Array (4 test cases)
        (3, "4\n1 2 3 4", "4 3 2 1", 0),
        (3, "1\n5", "5", 0),
        (3, "5\n10 20 30 40 50", "50 40 30 20 10", 0),
        (3, "6\n9 8 7 6 5 4", "4 5 6 7 8 9", 1),

        # Problem 4: Second Largest (5 test cases)
        (4, "6\n12 35 1 10 34 1", "34", 0),
        (4, "3\n10 10 10", "-1", 0),
        (4, "2\n5 10", "5", 0),
        (4, "5\n100 90 80 70 60", "90", 1),
        (4, "1\n42", "-1", 1),

        # Problem 5: Count Occurrences (4 test cases)
        (5, "6 2\n1 2 2 3 2 4", "3", 0),
        (5, "3 7\n5 9 12", "0", 0),
        (5, "4 5\n5 5 5 5", "4", 0),
        (5, "5 10\n10 20 10 30 10", "3", 1),

        # Problem 6: Sum Linked List (4 test cases)
        (6, "4\n1 2 3 4", "10", 0),
        (6, "0\n", "0", 0),
        (6, "3\n10 20 30", "60", 0),
        (6, "5\n5 5 5 5 5", "25", 1),

        # Problem 7: Reverse Linked List (4 test cases)
        (7, "3\n1 2 3", "3 2 1", 0),
        (7, "1\n42", "42", 0),
        (7, "0\n", "", 0),
        (7, "5\n10 20 30 40 50", "50 40 30 20 10", 1),

        # Problem 8: Find Middle Node (4 test cases)
        (8, "5\n1 2 3 4 5", "3", 0),
        (8, "4\n10 20 30 40", "30", 0),
        (8, "1\n99", "99", 0),
        (8, "6\n1 2 3 4 5 6", "4", 1),

        # Problem 9: Count Nodes (4 test cases)
        (9, "3\n10 20 30", "3", 0),
        (9, "0\n", "0", 0),
        (9, "1\n7", "1", 0),
        (9, "7\n1 2 3 4 5 6 7", "7", 1),

        # Problem 10: Detect Value in List (5 test cases)
        (10, "3 15\n5 15 25", "1", 0),
        (10, "3 99\n1 2 3", "0", 0),
        (10, "0 5\n", "0", 0),
        (10, "4 40\n10 20 30 40", "1", 1),
        (10, "4 10\n10 20 30 40", "1", 1)
    ]

    cursor.executemany("""
    INSERT INTO test_case (problem_id, input, expected_output, is_hidden)
    VALUES (?, ?, ?, ?);
    """, test_cases_data)

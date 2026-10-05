"""
Re:Learn - C Function Test Harness Generator and Driver
Wraps student functions in a test runner and maps GCC error lines back to student code.
"""

from typing import Tuple, Dict

PREAMBLE_COMMON = """#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>

struct Node {
    int val;
    struct Node* next;
};

static struct Node* createNode(int val) {
    struct Node* n = (struct Node*)malloc(sizeof(struct Node));
    if (n) {
        n->val = val;
        n->next = NULL;
    }
    return n;
}

static struct Node* buildList(int arr[], int n) {
    if (n <= 0) return NULL;
    struct Node* head = createNode(arr[0]);
    struct Node* curr = head;
    for (int i = 1; i < n; i++) {
        curr->next = createNode(arr[i]);
        curr = curr->next;
    }
    return head;
}

static void freeList(struct Node* head) {
    while (head != NULL) {
        struct Node* tmp = head;
        head = head->next;
        free(tmp);
    }
}
"""

HARNESS_DRIVERS: Dict[int, str] = {
    # 1. findMax(arr, n)
    1: """
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    if (n <= 0) return 0;
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    int res = findMax(arr, n);
    printf("%d", res);
    free(arr);
    return 0;
}
""",
    # 2. sumArray(arr, n)
    2: """
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    if (n == 0) {
        int res = sumArray(NULL, 0);
        printf("%d", res);
        return 0;
    }
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    int res = sumArray(arr, n);
    printf("%d", res);
    free(arr);
    return 0;
}
""",
    # 3. reverseArray(arr, n)
    3: """
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    if (n <= 0) return 0;
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    reverseArray(arr, n);
    for (int i = 0; i < n; i++) {
        printf("%d%s", arr[i], (i == n - 1) ? "" : " ");
    }
    free(arr);
    return 0;
}
""",
    # 4. secondLargest(arr, n)
    4: """
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    if (n <= 0) return 0;
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    int res = secondLargest(arr, n);
    printf("%d", res);
    free(arr);
    return 0;
}
""",
    # 5. countOccurrences(arr, n, target)
    5: """
int main(void) {
    int n, target;
    if (scanf("%d %d", &n, &target) != 2) return 0;
    if (n <= 0) {
        int res = countOccurrences(NULL, 0, target);
        printf("%d", res);
        return 0;
    }
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    int res = countOccurrences(arr, n, target);
    printf("%d", res);
    free(arr);
    return 0;
}
""",
    # 6. sumList(head)
    6: """
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    if (n == 0) {
        int res = sumList(NULL);
        printf("%d", res);
        return 0;
    }
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    struct Node* head = buildList(arr, n);
    int res = sumList(head);
    printf("%d", res);
    freeList(head);
    free(arr);
    return 0;
}
""",
    # 7. reverseList(head)
    7: """
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    if (n == 0) {
        struct Node* res = reverseList(NULL);
        if (res != NULL) printf("error");
        return 0;
    }
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    struct Node* head = buildList(arr, n);
    struct Node* newHead = reverseList(head);
    struct Node* curr = newHead;
    while (curr != NULL) {
        printf("%d%s", curr->val, (curr->next != NULL) ? " " : "");
        curr = curr->next;
    }
    freeList(newHead);
    free(arr);
    return 0;
}
""",
    # 8. findMiddle(head)
    8: """
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    if (n == 0) {
        int res = findMiddle(NULL);
        printf("%d", res);
        return 0;
    }
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    struct Node* head = buildList(arr, n);
    int res = findMiddle(head);
    printf("%d", res);
    freeList(head);
    free(arr);
    return 0;
}
""",
    # 9. countNodes(head)
    9: """
int main(void) {
    int n;
    if (scanf("%d", &n) != 1) return 0;
    if (n == 0) {
        int res = countNodes(NULL);
        printf("%d", res);
        return 0;
    }
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    struct Node* head = buildList(arr, n);
    int res = countNodes(head);
    printf("%d", res);
    freeList(head);
    free(arr);
    return 0;
}
""",
    # 10. detectValue(head, target)
    10: """
int main(void) {
    int n, target;
    if (scanf("%d %d", &n, &target) != 2) return 0;
    if (n == 0) {
        int res = detectValue(NULL, target);
        printf("%d", res);
        return 0;
    }
    int* arr = (int*)malloc(sizeof(int) * n);
    for (int i = 0; i < n; i++) {
        if (scanf("%d", &arr[i]) != 1) { free(arr); return 0; }
    }
    struct Node* head = buildList(arr, n);
    int res = detectValue(head, target);
    printf("%d", res);
    freeList(head);
    free(arr);
    return 0;
}
"""
}

def generate_harness(problem_id: int, student_code: str) -> Tuple[str, int]:
    """
    Returns (full_c_code, line_offset).
    line_offset is the number of lines before student_code starts.
    """
    preamble = PREAMBLE_COMMON.strip() + "\n\n"
    preamble_lines = preamble.count("\n")

    driver = HARNESS_DRIVERS.get(problem_id, """
int main(void) {
    return 0;
}
""")
    full_code = f"{preamble}{student_code.strip()}\n{driver}"
    return full_code, preamble_lines

def map_error_line_to_student(raw_line: int, line_offset: int, student_code_lines: int) -> int:
    """
    Maps GCC raw error line back to student code line (1-indexed).
    If it falls inside student code, returns mapped line. Otherwise returns 1 or student_code_lines.
    """
    mapped = raw_line - line_offset
    if 1 <= mapped <= student_code_lines:
        return mapped
    if mapped < 1:
        return 1
    return student_code_lines

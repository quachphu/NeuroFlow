import json
from fastmcp import FastMCP

mcp = FastMCP("NeuroFlowCanvas")

COURSES = {
    "CS170": {
        "name": "Data Structures & Algorithms",
        "instructor": "Dr. Patel",
        "schedule": "MWF 9:00-10:15",
        "credits": 4,
        "current_grade": 88.2,
        "letter_grade": "B+",
        "grade_breakdown": {
            "Midterm (25%)": 82,
            "Homework (30%)": 94,
            "Labs (15%)": 90,
            "Final (30%)": None,
        },
        "assignments": [
            {"title": "HW5: Graph Algorithms", "due": "2026-03-30", "points": 100, "weight": "6%", "submitted": False},
            {"title": "Midterm", "due": "2026-03-26", "points": 200, "weight": "25%", "submitted": False, "type": "exam"},
            {"title": "Lab 6: Dijkstra Implementation", "due": "2026-04-02", "points": 50, "weight": "3%", "submitted": False},
            {"title": "Final Project", "due": "2026-04-15", "points": 300, "weight": "30%", "submitted": False},
        ],
        "syllabus_topics": [
            {"week": 1, "topic": "Complexity Analysis (Big-O, Omega, Theta)"},
            {"week": 2, "topic": "Arrays, Linked Lists, Stacks, Queues"},
            {"week": 3, "topic": "Trees and Binary Search Trees"},
            {"week": 4, "topic": "Heaps and Priority Queues"},
            {"week": 5, "topic": "Hash Tables and Collision Resolution"},
            {"week": 6, "topic": "Sorting Algorithms (Merge Sort, Quick Sort)"},
            {"week": 7, "topic": "Graph Representations and Traversal (BFS, DFS)"},
            {"week": 8, "topic": "Uninformed Search (BFS, DFS, Iterative Deepening)"},
            {"week": 9, "topic": "Informed Search (A*, Heuristics, Admissibility)"},
            {"week": 10, "topic": "Adversarial Search (Minimax, Alpha-Beta Pruning)"},
        ],
        "exam_topics": [
            "A* search and heuristic functions",
            "Admissibility and consistency of heuristics",
            "BFS vs DFS time/space complexity",
            "Graph representations (adjacency list vs matrix)",
            "Dijkstra's algorithm",
            "Sorting algorithm comparisons",
        ],
    },
    "CS105": {
        "name": "Intro to Computer Science",
        "instructor": "Prof. Kim",
        "schedule": "MWF 14:00-15:15",
        "credits": 3,
        "current_grade": 92.1,
        "letter_grade": "A-",
        "grade_breakdown": {
            "Programming Assignments (40%)": 95,
            "Labs (20%)": 88,
            "Midterm (15%)": 90,
            "Final (25%)": None,
        },
        "assignments": [
            {"title": "PA3: OOP Basics", "due": "2026-04-02", "points": 100, "weight": "10%", "submitted": False},
            {"title": "Lab 4: File I/O", "due": "2026-03-25", "points": 30, "weight": "4%", "submitted": False},
        ],
        "syllabus_topics": [
            {"week": 1, "topic": "Variables, Types, and Control Flow"},
            {"week": 2, "topic": "Functions and Scope"},
            {"week": 3, "topic": "Lists, Tuples, Dictionaries"},
            {"week": 4, "topic": "File I/O and Exception Handling"},
            {"week": 5, "topic": "Object-Oriented Programming"},
            {"week": 6, "topic": "Inheritance and Polymorphism"},
        ],
        "exam_topics": [],
    },
    "EE120": {
        "name": "Signals & Systems",
        "instructor": "Prof. Freeman",
        "schedule": "TTh 14:00-15:30",
        "credits": 4,
        "current_grade": 85.5,
        "letter_grade": "B",
        "grade_breakdown": {
            "Midterm 1 (20%)": 82,
            "Midterm 2 (25%)": None,
            "Homework (25%)": 90,
            "Final (30%)": None,
        },
        "assignments": [
            {"title": "HW6: Convolution & LTI Systems", "due": "2026-03-28", "points": 100, "weight": "5%", "submitted": False},
            {"title": "Midterm 2", "due": "2026-04-02", "points": 200, "weight": "25%", "submitted": False, "type": "exam"},
        ],
        "syllabus_topics": [
            {"week": 1, "topic": "Signals: Continuous and Discrete"},
            {"week": 2, "topic": "System Properties: Linearity, Time-Invariance, Causality"},
            {"week": 3, "topic": "Input-Output Relationships and Abstraction"},
            {"week": 4, "topic": "LTI Systems and Impulse Response"},
            {"week": 5, "topic": "Convolution"},
            {"week": 6, "topic": "Fourier Series"},
            {"week": 7, "topic": "Fourier Transform"},
            {"week": 8, "topic": "Frequency Response and Filtering"},
            {"week": 9, "topic": "Sampling and Aliasing"},
            {"week": 10, "topic": "Z-Transform and Discrete Systems"},
        ],
        "exam_topics": [
            "Input-output relationships and system abstraction",
            "System properties (linearity, time-invariance, causality, stability)",
            "LTI systems and impulse response",
            "Convolution (continuous and discrete)",
            "Fourier series and Fourier transform",
            "Frequency response of LTI systems",
            "Signal representations (continuous vs discrete)",
        ],
    },
    "ECON101": {
        "name": "Principles of Microeconomics",
        "instructor": "Dr. Chen",
        "schedule": "TTh 10:00-11:15",
        "credits": 3,
        "current_grade": 94.0,
        "letter_grade": "A",
        "grade_breakdown": {
            "Problem Sets (25%)": 96,
            "Midterm 1 (20%)": 91,
            "Midterm 2 (20%)": None,
            "Final (35%)": None,
        },
        "assignments": [
            {"title": "Problem Set 6", "due": "2026-03-28", "points": 50, "weight": "5%", "submitted": False},
            {"title": "Midterm 2", "due": "2026-04-03", "points": 100, "weight": "20%", "submitted": False, "type": "exam"},
        ],
        "syllabus_topics": [
            {"week": 1, "topic": "Supply and Demand"},
            {"week": 2, "topic": "Elasticity"},
            {"week": 3, "topic": "Consumer and Producer Surplus"},
            {"week": 4, "topic": "Market Efficiency and Market Failure"},
            {"week": 5, "topic": "Externalities and Public Goods"},
        ],
        "exam_topics": [],
    },
}


def _resolve_course_id(course_id: str) -> str | None:
    upper = course_id.upper().replace(" ", "")
    if upper in COURSES:
        return upper
    aliases = {
        "DATA STRUCTURES": "CS170", "ALGORITHMS": "CS170", "DSA": "CS170",
        "INTRO": "CS105", "INTROCS": "CS105",
        "SIGNALS": "EE120", "SYSTEMS": "EE120", "EE": "EE120",
        "ECON": "ECON101", "MICROECONOMICS": "ECON101",
    }
    for alias, cid in aliases.items():
        if alias in upper:
            return cid
    return None


@mcp.tool()
def get_courses() -> str:
    """Get all enrolled courses this quarter with current grades."""
    summary = []
    for cid, c in COURSES.items():
        pending = [a for a in c["assignments"] if not a["submitted"]]
        summary.append({
            "course_id": cid,
            "name": c["name"],
            "instructor": c["instructor"],
            "current_grade": c["current_grade"],
            "letter_grade": c["letter_grade"],
            "pending_assignments": len(pending),
        })
    return json.dumps({"courses": summary})


@mcp.tool()
def get_assignments(course_id: str) -> str:
    """Get upcoming assignments for a course with due dates and weights."""
    cid = _resolve_course_id(course_id)
    if not cid:
        return json.dumps({"error": f"Course '{course_id}' not found"})
    course = COURSES[cid]
    pending = [a for a in course["assignments"] if not a["submitted"]]
    return json.dumps({
        "course_id": cid,
        "course_name": course["name"],
        "assignments": pending,
    })


@mcp.tool()
def get_grades(course_id: str) -> str:
    """Get current grade and breakdown for a course."""
    cid = _resolve_course_id(course_id)
    if not cid:
        return json.dumps({"error": f"Course '{course_id}' not found"})
    course = COURSES[cid]
    return json.dumps({
        "course_id": cid,
        "course_name": course["name"],
        "current_grade": course["current_grade"],
        "letter_grade": course["letter_grade"],
        "breakdown": course["grade_breakdown"],
    })


@mcp.tool()
def get_syllabus(course_id: str) -> str:
    """Get syllabus topics and exam-critical terms for a course."""
    cid = _resolve_course_id(course_id)
    if not cid:
        return json.dumps({"error": f"Course '{course_id}' not found"})
    course = COURSES[cid]
    return json.dumps({
        "course_id": cid,
        "course_name": course["name"],
        "syllabus": course["syllabus_topics"],
        "exam_topics": course["exam_topics"],
    })

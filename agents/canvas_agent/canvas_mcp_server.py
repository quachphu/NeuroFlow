import json
from datetime import datetime

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
            {"title": "Midterm", "due": "2026-04-01", "points": 200, "weight": "25%", "submitted": False, "type": "exam"},
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
    "CS180": {
        "name": "Introduction to Artificial Intelligence",
        "instructor": "Prof. Russell",
        "schedule": "TTh 10:00-11:15",
        "credits": 4,
        "current_grade": 87.0,
        "letter_grade": "B+",
        "grade_breakdown": {
            "Midterm (25%)": None,
            "Homework (30%)": 91,
            "Project (15%)": None,
            "Final (30%)": None,
        },
        "assignments": [
            {"title": "HW5: Search Algorithms", "due": "2026-03-28", "points": 100, "weight": "6%", "submitted": False},
            {"title": "AI Midterm", "due": "2026-03-26", "points": 200, "weight": "25%", "submitted": False, "type": "exam"},
            {"title": "Project: Multi-Agent System", "due": "2026-04-10", "points": 300, "weight": "15%", "submitted": False},
        ],
        "syllabus_topics": [
            {"week": 1, "topic": "Introduction to AI and Intelligent Agents"},
            {"week": 2, "topic": "Uninformed Search (BFS, DFS, Iterative Deepening)"},
            {"week": 3, "topic": "Informed Search (A*, Heuristics, Admissibility)"},
            {"week": 4, "topic": "Adversarial Search (Minimax, Alpha-Beta Pruning)"},
            {"week": 5, "topic": "Constraint Satisfaction Problems"},
            {"week": 6, "topic": "Knowledge Representation and Propositional Logic"},
            {"week": 7, "topic": "First-Order Logic and Inference"},
            {"week": 8, "topic": "Bayesian Networks and Probabilistic Reasoning"},
            {"week": 9, "topic": "Machine Learning Fundamentals"},
            {"week": 10, "topic": "Neural Networks and Deep Learning"},
            {"week": 11, "topic": "Natural Language Processing"},
        ],
        "exam_topics": [
            "A* search and heuristic functions",
            "Admissibility and consistency of heuristics",
            "Minimax and alpha-beta pruning",
            "Knowledge representation",
            "Bayesian networks and probabilistic inference",
            "Constraint satisfaction problems",
        ],
    },
}


def _resolve_course_id(course_id: str) -> str | None:
    upper = course_id.upper().replace(" ", "")
    if upper in COURSES:
        return upper
    aliases = {
        "DATA STRUCTURES": "CS170", "ALGORITHMS": "CS170", "DSA": "CS170",
        "INTRO": "CS105", "INTROCS": "CS105",
        "AI": "CS180", "ARTIFICIAL": "CS180", "INTELLIGENCE": "CS180", "CS180": "CS180",
    }
    for alias, cid in aliases.items():
        if alias in upper:
            return cid
    return None


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


def get_all_upcoming(days: int = 14) -> str:
    """Get all upcoming assignments across all courses, sorted by due date.
    Useful for the Advisor to know what the student needs to study for."""
    from datetime import timedelta
    today = datetime.now().date()
    cutoff = today + timedelta(days=days)
    upcoming = []
    for cid, c in COURSES.items():
        for a in c["assignments"]:
            if a["submitted"]:
                continue
            due = datetime.strptime(a["due"], "%Y-%m-%d").date()
            if due <= cutoff:
                days_left = (due - today).days
                upcoming.append({
                    "course_id": cid,
                    "course_name": c["name"],
                    "title": a["title"],
                    "due": a["due"],
                    "days_left": days_left,
                    "points": a["points"],
                    "weight": a["weight"],
                    "is_exam": a.get("type") == "exam",
                    "current_grade": c["current_grade"],
                })
    upcoming.sort(key=lambda x: x["days_left"])
    return json.dumps({"upcoming": upcoming, "total": len(upcoming)})

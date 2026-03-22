import json
from openai import OpenAI
from agents.models.config import TASK_SEED, ASI1_API_KEY
from agents.models.models import SharedAgentState
from uagents import Agent, Context

task_agent = Agent(
    name="neuroflow-task",
    seed=TASK_SEED,
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)

DECOMPOSITION_PROMPT = """You are a task decomposition assistant for people with ADHD.

Given a task description, break it into concrete micro-steps following these rules:
1. Each step starts with a verb (Open, Write, Read, Create, etc.)
2. Each step takes MAX 15 minutes
3. The first 2 steps must be trivially easy (under 3 minutes) — this is the "activation runway"
4. Insert a break step every 3-4 work steps
5. Steps should be specific and concrete, not vague
6. Maximum 15 steps total

Return ONLY valid JSON in this exact format:
{"steps": [{"step": 1, "description": "Open Google Scholar in your browser", "duration_min": 2, "difficulty": "easy"}, ...]}"""


def get_llm_client():
    if ASI1_API_KEY:
        return OpenAI(base_url="https://api.asi1.ai/v1", api_key=ASI1_API_KEY)
    from agents.models.config import OPENAI_API_KEY
    if OPENAI_API_KEY:
        return OpenAI(api_key=OPENAI_API_KEY)
    return None


async def decompose_task(ctx: Context, task_description: str) -> list[dict]:
    """Use LLM to decompose a task into ADHD-friendly micro-steps."""
    client = get_llm_client()
    if not client:
        return [
            {"step": 1, "description": f"Start working on: {task_description}", "duration_min": 15, "difficulty": "medium"}
        ]

    try:
        response = client.chat.completions.create(
            model="asi1-mini",
            messages=[
                {"role": "system", "content": DECOMPOSITION_PROMPT},
                {"role": "user", "content": f"Decompose this task: {task_description}"},
            ],
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        return parsed.get("steps", [])
    except Exception as e:
        ctx.logger.error(f"LLM decomposition failed: {e}")
        return [
            {"step": 1, "description": f"Start working on: {task_description}", "duration_min": 15, "difficulty": "medium"}
        ]


def get_tasks(ctx: Context) -> dict:
    """Get all tasks from storage."""
    return json.loads(ctx.storage.get("tasks") or "{}")


def save_tasks(ctx: Context, tasks: dict):
    ctx.storage.set("tasks", json.dumps(tasks))


async def handle_task_query(ctx: Context, query: str) -> str:
    """Route task-related queries to the right action."""
    lower = query.lower()
    tasks = get_tasks(ctx)

    if any(kw in lower for kw in ["mark", "done", "complete", "finished"]):
        return mark_step_complete(ctx, tasks, lower)

    if any(kw in lower for kw in ["progress", "status", "how am i", "where am i"]):
        return get_progress(tasks)

    if any(kw in lower for kw in ["next", "what should", "what's next"]):
        return get_next_step(tasks)

    return await create_new_task(ctx, query)


async def create_new_task(ctx: Context, task_description: str) -> str:
    tasks = get_tasks(ctx)
    task_id = f"task_{len(tasks) + 1}"
    steps = await decompose_task(ctx, task_description)

    tasks[task_id] = {
        "description": task_description,
        "steps": steps,
        "completed_steps": [],
    }
    save_tasks(ctx, tasks)

    step_list = "\n".join(
        f"  Step {s['step']} ({s['duration_min']} min, {s['difficulty']}): {s['description']}"
        for s in steps[:5]
    )
    total = len(steps)
    showing = min(5, total)

    return json.dumps({
        "action": "task_created",
        "task_id": task_id,
        "description": task_description,
        "total_steps": total,
        "showing": showing,
        "steps_preview": step_list,
        "message": f"Broke '{task_description}' into {total} steps. First 2 are quick wins to get you started.",
    })


def mark_step_complete(ctx: Context, tasks: dict, query: str) -> str:
    if not tasks:
        return json.dumps({"error": "No tasks yet. Tell me what you need to work on."})

    latest_id = list(tasks.keys())[-1]
    task = tasks[latest_id]
    completed = task["completed_steps"]
    all_steps = task["steps"]
    next_step_num = len(completed) + 1

    if next_step_num > len(all_steps):
        return json.dumps({
            "action": "task_complete",
            "message": f"All {len(all_steps)} steps are done! You finished '{task['description']}'.",
        })

    completed.append(next_step_num)
    save_tasks(ctx, tasks)

    done = len(completed)
    total = len(all_steps)
    next_desc = all_steps[done]["description"] if done < total else "You're done!"

    return json.dumps({
        "action": "step_completed",
        "completed": done,
        "total": total,
        "percent": round(done / total * 100),
        "next_step": next_desc,
        "message": f"Step {next_step_num} done! {done}/{total} complete ({round(done/total*100)}%).",
    })


def get_progress(tasks: dict) -> str:
    if not tasks:
        return json.dumps({"sessions": 0, "message": "No tasks yet."})

    results = []
    for tid, task in tasks.items():
        done = len(task["completed_steps"])
        total = len(task["steps"])
        results.append({
            "task_id": tid,
            "description": task["description"],
            "completed": done,
            "total": total,
            "percent": round(done / total * 100) if total else 0,
        })

    return json.dumps({"action": "progress", "tasks": results})


def get_next_step(tasks: dict) -> str:
    if not tasks:
        return json.dumps({"message": "No tasks yet. Tell me what you need to work on."})

    latest_id = list(tasks.keys())[-1]
    task = tasks[latest_id]
    done = len(task["completed_steps"])
    all_steps = task["steps"]

    if done >= len(all_steps):
        return json.dumps({"message": f"You finished '{task['description']}'! Ready for a new task?"})

    step = all_steps[done]
    return json.dumps({
        "action": "next_step",
        "task": task["description"],
        "step_number": done + 1,
        "total": len(all_steps),
        "description": step["description"],
        "duration_min": step["duration_min"],
        "difficulty": step["difficulty"],
    })


@task_agent.on_message(SharedAgentState)
async def handle_message(ctx: Context, sender: str, state: SharedAgentState):
    ctx.logger.info(f"Received: session={state.chat_session_id}, query={state.query!r}")
    state.result = await handle_task_query(ctx, state.query)
    await ctx.send(sender, state)


if __name__ == "__main__":
    task_agent.run()

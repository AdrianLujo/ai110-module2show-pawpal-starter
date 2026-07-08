# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

## 🖥️ Sample Output

Paste a sample of your app's CLI or Streamlit output here so a reader can see what a generated plan looks like:

```
➜  ai110-module2show-pawpal-starter git:(main) ✗ python main.py
Today's Schedule
========================================
Daily plan for Jordan (90 min available):
  08:00 — Morning walk (30 min) [priority: high]
  08:30 — Feeding (10 min) [priority: high]
  08:40 — Playtime (20 min) [priority: medium]
```

## 🧪 Testing PawPal+

```bash
# Run the full test suite:
pytest

# Run with coverage:
pytest --cov
```

Sample test output:

```
# Paste your pytest output here
```

## 📐 Smarter Scheduling

PawPal+ goes beyond a flat to-do list. All logic lives in `pawpal_system.py`.

| Feature | Method(s) | Notes |
|---------|-----------|-------|
| Sorting | `Scheduler.sort_by_time()`, `Scheduler.sort_by_priority()` | Order tasks chronologically or by importance |
| Filtering | `Scheduler.filter_tasks()`, `Scheduler.filter_by_time()` | By pet name / completion status, or by the owner's time budget |
| Conflict detection | `Scheduler.detect_conflicts()` | Warns (never crashes) when tasks share a start time |
| Recurring tasks | `Pet.mark_task_complete()`, `Task.next_occurrence()` | Completing a daily/weekly task spawns its next occurrence |

### Sorting behavior

- **`Scheduler.sort_by_time()`** returns all of the owner's tasks sorted earliest-first by their `"HH:MM"` start time. Because that format is zero-padded and fixed-width, sorting the strings alphabetically already matches chronological order — no time parsing needed.
- **`Scheduler.sort_by_priority()`** returns the owner's *pending* tasks sorted highest-priority first, using the `Priority` enum (`HIGH > MEDIUM > LOW`).

### Filtering behavior

- **`Scheduler.filter_tasks(done=None, pet_name=None)`** filters the owner's tasks by completion status and/or pet name. Passing `done=False` keeps only pending tasks, `pet_name="Mochi"` keeps only that pet's tasks, and `None` on either argument ignores that filter.
- **`Scheduler.filter_by_time()`** greedily keeps tasks that fit within the owner's available minutes, dropping the rest — so sorting by priority first protects the important tasks.

### Conflict detection logic

- **`Scheduler.detect_conflicts()`** groups pending tasks by their `"HH:MM"` start time and returns a list of warning strings for any time slot holding two or more tasks. It catches clashes across *different* pets as well as within one pet, skips done/timeless tasks, and returns an empty list when nothing collides — so it warns rather than crashing the program.
- Note: the detector only flags exact time matches; the plan itself resolves duration overlaps separately via `Scheduler.resolve_conflicts()`, which pushes overlapping slots back so nothing double-books.

### Recurring task logic

- **`Pet.mark_task_complete(task)`** marks a task done and, if it recurs, automatically creates and attaches its next occurrence to the pet, returning the new task (or `None` for a one-off).
- **`Task.next_occurrence()`** produces the follow-up task with a fresh due date computed with `timedelta` — today + 1 day for `"daily"`, today + 7 days for `"weekly"`.

## 📸 Demo Walkthrough

Describe your app in numbered steps so a reader can follow along without watching a video:

1. <!-- Describe this step -->
2. <!-- Describe this step -->
3. <!-- Describe this step -->
4. <!-- Describe this step -->
5. <!-- Add more steps as needed -->

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or link to a demo video here -->

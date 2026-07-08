"""PawPal+ system implementation.

Core logic for the four classes: Task, Pet, Owner, Scheduler.

Design decisions:
- Priority is an IntEnum so tasks sort by importance with no lookup table.
- ScheduledTask pairs a Task with a concrete start/end time, so the plan can
  express *when* something happens and detect overlaps.
- Pet.tasks is the single source of truth. The Owner aggregates across pets via
  all_tasks(); the Scheduler reads tasks through the Owner, never the pets.
- The Scheduler plans across ALL of an owner's pets.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import IntEnum


class Priority(IntEnum):
    """Higher value = more important, so tasks sort naturally."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


def _add_minutes(start: time, minutes: int) -> time:
    """Return the time `minutes` after `start` (same day)."""
    return (datetime.combine(date.min, start) + timedelta(minutes=minutes)).time()


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: Priority
    recurring: bool = False
    done: bool = False
    notes: str = ""

    def fits_in(self, minutes: int) -> bool:
        """Return True if this task fits within the given minutes."""
        return self.duration_minutes <= minutes

    def mark_complete(self) -> None:
        """Mark this task complete."""
        self.done = True

    def mark_incomplete(self) -> None:
        """Mark this task not complete."""
        self.done = False


@dataclass
class ScheduledTask:
    """A Task placed at a concrete time in the plan."""
    task: Task
    start: time
    end: time

    def overlaps(self, other: "ScheduledTask") -> bool:
        """Return True if this slot's time range overlaps another's."""
        return self.start < other.end and other.start < self.end


@dataclass
class Pet:
    name: str
    species: str
    breed: str = ""
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet."""
        self.tasks.append(task)

    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet (no-op if it isn't attached)."""
        if task in self.tasks:
            self.tasks.remove(task)

    def pending_tasks(self) -> list[Task]:
        """Return this pet's not-yet-completed tasks."""
        return [t for t in self.tasks if not t.done]


@dataclass
class Owner:
    name: str
    minutes_available: int = 0
    preferences: list[str] = field(default_factory=list)
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self.pets.append(pet)

    def set_availability(self, minutes: int) -> None:
        """Set how many minutes the owner has available today."""
        self.minutes_available = minutes

    def add_preference(self, pref: str) -> None:
        """Record an owner preference."""
        self.preferences.append(pref)

    def all_tasks(self) -> list[Task]:
        """Aggregate every task across all of this owner's pets."""
        return [task for pet in self.pets for task in pet.tasks]


class Scheduler:
    def __init__(self, owner: Owner, day_start: time = time(8, 0)):
        self.owner = owner
        self.day_start = day_start

    def sort_by_priority(self) -> list[Task]:
        """Return the owner's pending tasks, highest priority first."""
        pending = [t for t in self.owner.all_tasks() if not t.done]
        return sorted(pending, key=lambda t: t.priority, reverse=True)

    def filter_by_time(self, tasks: list[Task]) -> list[Task]:
        """Keep tasks that fit within the owner's available minutes.

        Greedy: walks the list in order and keeps a running time budget, so
        callers should sort by priority first to protect important tasks.
        """
        remaining = self.owner.minutes_available
        kept: list[Task] = []
        for task in tasks:
            if task.fits_in(remaining):
                kept.append(task)
                remaining -= task.duration_minutes
        return kept

    def _assign_slots(self, tasks: list[Task]) -> list[ScheduledTask]:
        """Lay tasks back-to-back starting at day_start."""
        scheduled: list[ScheduledTask] = []
        cursor = self.day_start
        for task in tasks:
            end = _add_minutes(cursor, task.duration_minutes)
            scheduled.append(ScheduledTask(task, cursor, end))
            cursor = end
        return scheduled

    def resolve_conflicts(self, scheduled: list[ScheduledTask]) -> list[ScheduledTask]:
        """Push back any overlapping slots so none collide, keeping order."""
        result: list[ScheduledTask] = []
        cursor: time | None = None
        for item in sorted(scheduled, key=lambda s: s.start):
            start = item.start
            if cursor is not None and start < cursor:
                start = cursor
            end = _add_minutes(start, item.task.duration_minutes)
            result.append(ScheduledTask(item.task, start, end))
            cursor = end
        return result

    def build_plan(self) -> list[ScheduledTask]:
        """Produce the ordered daily plan with concrete time slots."""
        ordered = self.sort_by_priority()
        affordable = self.filter_by_time(ordered)
        scheduled = self._assign_slots(affordable)
        return self.resolve_conflicts(scheduled)

    def explain_plan(self) -> str:
        """Human-readable plan and the reasoning behind it."""
        plan = self.build_plan()
        if not plan:
            return "No plan: no pending tasks, or no time available."
        lines = [
            f"Daily plan for {self.owner.name} "
            f"({self.owner.minutes_available} min available):"
        ]
        for item in plan:
            task = item.task
            lines.append(
                f"  {item.start.strftime('%H:%M')} — {task.title} "
                f"({task.duration_minutes} min) [priority: {task.priority.name.lower()}]"
            )
        return "\n".join(lines)

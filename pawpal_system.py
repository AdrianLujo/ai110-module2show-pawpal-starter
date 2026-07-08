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

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import IntEnum


# How far ahead the next occurrence of a recurring task falls. Anything not in
# this table is treated as a one-off task that does not repeat.
_FREQUENCY_DELTAS: dict[str, timedelta] = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
}


class Priority(IntEnum):
    """Higher value = more important, so tasks sort naturally."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3


def _add_minutes(start: time, minutes: int) -> time:
    """Return the time `minutes` after `start`, clamped to end-of-day.

    This is a single-day planner, so a task that would spill past midnight is
    pinned at the last instant of the day rather than wrapping around to the
    small hours — which would otherwise make an end time fall *before* its
    start and send resolve_conflicts()'s cursor backwards.
    """
    combined = datetime.combine(date.min, start) + timedelta(minutes=minutes)
    if combined.date() > date.min:
        return time.max
    return combined.time()


def _parse_time(value: str, fallback: time) -> time:
    """Parse an "HH:MM" string into a time; use `fallback` when unset/invalid.

    Never raises — a blank or malformed value falls back rather than crashing
    the whole plan over one bad task. Accepts non-zero-padded input like
    "9:00" as well as "09:00".
    """
    if not value:
        return fallback
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return fallback


def _canonical_time(value: str) -> str:
    """Normalize an "HH:MM" string so equivalent forms compare equal.

    "9:00" and "09:00" are the same clock time; both become "09:00". A blank
    or malformed value is returned unchanged so it neither merges with real
    slots nor crashes.
    """
    try:
        return datetime.strptime(value, "%H:%M").strftime("%H:%M")
    except ValueError:
        return value


@dataclass
class Task:
    """A single thing to do for a pet, with duration, priority, and timing."""
    title: str
    duration_minutes: int
    priority: Priority
    time: str = ""  # preferred start time in "HH:MM" (24-hour) format
    frequency: str = ""  # "daily", "weekly", or "" for a one-off task
    due_date: date | None = None
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

    def _frequency_key(self) -> str:
        """Normalize the frequency for lookups: trimmed and lower-cased."""
        return self.frequency.strip().lower()

    def is_recurring(self) -> bool:
        """Return True if this task repeats on a known frequency."""
        return self._frequency_key() in _FREQUENCY_DELTAS

    def next_occurrence(self, from_date: date | None = None) -> "Task":
        """Return a fresh, not-done copy of this task for its next occurrence.

        The new due date is `from_date` (default: today) plus one interval —
        one day for "daily", one week for "weekly". timedelta handles the
        arithmetic correctly across month and year boundaries, so we never do
        manual day/month rollover math ourselves.
        """
        if not self.is_recurring():
            raise ValueError(
                f"{self.title!r} has no recurring frequency to advance"
            )
        base = from_date or date.today()
        next_due = base + _FREQUENCY_DELTAS[self._frequency_key()]
        # replace() copies every other field (title, duration, priority, ...)
        # so only the due date and completion status change.
        return replace(self, due_date=next_due, done=False)


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
    """A pet owned by an Owner; holds its own list of tasks."""
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

    def mark_task_complete(self, task: Task) -> Task | None:
        """Mark one of this pet's tasks complete, auto-repeating if recurring.

        When a "daily" or "weekly" task is completed, its next occurrence is
        created and attached to this pet automatically. Returns that new
        follow-up task, or None for a one-off task. This logic lives on Pet
        (not Task) because only the pet owns the task list the new instance
        must be added to.

        Re-completing a task that is already done is a no-op: it returns None
        rather than spawning a duplicate follow-up.
        """
        if task.done:
            return None
        task.mark_complete()
        if not task.is_recurring():
            return None
        follow_up = task.next_occurrence()
        self.add_task(follow_up)
        return follow_up


@dataclass
class Owner:
    """A pet owner with a daily time budget, preferences, and pets."""
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
    """Builds an owner's daily plan across all their pets' tasks."""

    def __init__(self, owner: Owner, day_start: time = time(8, 0)):
        """Plan for the given owner's pets.

        Each task is placed at its own `time`; day_start is only the fallback
        start for tasks that have no time set.
        """
        self.owner = owner
        self.day_start = day_start

    def sort_by_priority(self) -> list[Task]:
        """Return the owner's pending tasks, highest priority first."""
        pending = [t for t in self.owner.all_tasks() if not t.done]
        return sorted(pending, key=lambda t: t.priority, reverse=True)

    def sort_by_time(self) -> list[Task]:
        """Return the owner's tasks sorted by start time, earliest first.

        Each task's `time` is an "HH:MM" (24-hour) string, which we parse to a
        real time so that chronological order holds even for non-zero-padded
        input like "9:00" (a raw string sort would put it after "10:00"). The
        key's leading flag keeps tasks with no time ("") sorting first.
        """
        return sorted(
            self.owner.all_tasks(),
            key=lambda t: (t.time != "", _parse_time(t.time, time.min)),
        )

    def filter_tasks(
        self, done: bool | None = None, pet_name: str | None = None
    ) -> list[Task]:
        """Filter the owner's tasks by completion status and/or pet name.

        - done=True keeps only completed tasks; done=False keeps only pending
          ones; done=None ignores completion status.
        - pet_name keeps only tasks belonging to the pet with that name;
          pet_name=None ignores which pet a task belongs to.
        """
        results: list[Task] = []
        for pet in self.owner.pets:
            if pet_name is not None and pet.name != pet_name:
                continue
            for task in pet.tasks:
                if done is not None and task.done != done:
                    continue
                results.append(task)
        return results

    def detect_conflicts(self) -> list[str]:
        """Return warning messages for tasks that share the same start time.

        Lightweight by design: it only groups pending tasks by their start
        time — no slot math, no mutation of the plan. Times are normalized
        first, so "9:00" and "09:00" collide as the same slot. Tasks with no
        time set ("") or already done are skipped, and clashes across
        different pets are caught just like clashes within one pet. Returns an
        empty list when nothing collides, so callers can print the result
        without any risk of crashing.
        """
        by_time: dict[str, list[tuple[str, Task]]] = {}
        for pet in self.owner.pets:
            for task in pet.tasks:
                if task.done or not task.time:
                    continue
                slot = _canonical_time(task.time)
                by_time.setdefault(slot, []).append((pet.name, task))

        warnings: list[str] = []
        for slot in sorted(by_time):
            entries = by_time[slot]
            if len(entries) > 1:
                labels = ", ".join(f"{task.title} ({pet})" for pet, task in entries)
                warnings.append(f"WARNING: {len(entries)} tasks scheduled at {slot} — {labels}")
        return warnings

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
        """Place each task at its own `time`, falling back to day_start.

        This is what unifies the planner with detect_conflicts(): both now read
        the same `time` attribute. Tasks whose time is unset land at day_start;
        resolve_conflicts() then pushes back any that overlap.
        """
        scheduled: list[ScheduledTask] = []
        for task in tasks:
            start = _parse_time(task.time, self.day_start)
            end = _add_minutes(start, task.duration_minutes)
            scheduled.append(ScheduledTask(task, start, end))
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
        """Produce the daily plan with concrete time slots.

        Priority decides which tasks make the time budget; each survivor is
        then placed at its own `time` and overlaps are pushed back, so the
        final plan is ordered chronologically by start time.

        Tasks explicitly due after today (e.g. a recurring task's next
        occurrence) are held out — this plan is for today. Tasks with no due
        date are always eligible.
        """
        today = date.today()
        ordered = [
            t for t in self.sort_by_priority()
            if t.due_date is None or t.due_date <= today
        ]
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

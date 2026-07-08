"""Tests for core PawPal+ behaviors."""

import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pawpal_system import Owner, Pet, Task, Priority, Scheduler


def test_mark_complete_changes_status():
    """Calling mark_complete() flips the task's done status to True."""
    task = Task("Morning walk", 30, Priority.HIGH)
    assert task.done is False

    task.mark_complete()

    assert task.done is True


def test_adding_task_increases_pet_task_count():
    """Adding a task to a pet increases that pet's task count by one."""
    pet = Pet(name="Mochi", species="dog")
    assert len(pet.tasks) == 0

    pet.add_task(Task("Feeding", 10, Priority.HIGH))

    assert len(pet.tasks) == 1


def test_completing_daily_task_spawns_next_occurrence():
    """A completed daily task auto-creates a fresh instance due tomorrow."""
    pet = Pet(name="Biscuit", species="cat")
    feeding = Task("Feeding", 10, Priority.HIGH, frequency="daily")
    pet.add_task(feeding)

    follow_up = pet.mark_task_complete(feeding)

    assert feeding.done is True
    assert follow_up is not None
    assert follow_up.done is False
    assert follow_up.due_date == date.today() + timedelta(days=1)
    assert len(pet.tasks) == 2


def test_completing_weekly_task_advances_by_seven_days():
    """A completed weekly task's next occurrence is due a week out."""
    pet = Pet(name="Mochi", species="dog")
    grooming = Task("Grooming", 45, Priority.LOW, frequency="weekly")
    pet.add_task(grooming)

    follow_up = pet.mark_task_complete(grooming)

    assert follow_up.due_date == date.today() + timedelta(weeks=1)


def test_completing_one_off_task_does_not_repeat():
    """A non-recurring task is completed without spawning a new instance."""
    pet = Pet(name="Mochi", species="dog")
    walk = Task("Morning walk", 30, Priority.HIGH)
    pet.add_task(walk)

    follow_up = pet.mark_task_complete(walk)

    assert follow_up is None
    assert len(pet.tasks) == 1


def test_detect_conflicts_flags_same_time_across_pets():
    """Two tasks at the same time (different pets) produce one warning."""
    owner = Owner(name="Jordan")
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Biscuit", species="cat")
    owner.add_pet(dog)
    owner.add_pet(cat)
    dog.add_task(Task("Vet call", 15, Priority.HIGH, time="12:15"))
    cat.add_task(Task("Playtime", 20, Priority.MEDIUM, time="12:15"))

    conflicts = Scheduler(owner).detect_conflicts()

    assert len(conflicts) == 1
    assert "12:15" in conflicts[0]


def test_detect_conflicts_empty_when_times_differ():
    """Distinct times produce no warnings (and never crash)."""
    owner = Owner(name="Jordan")
    dog = Pet(name="Mochi", species="dog")
    owner.add_pet(dog)
    dog.add_task(Task("Morning walk", 30, Priority.HIGH, time="07:00"))
    dog.add_task(Task("Grooming", 45, Priority.LOW, time="16:30"))

    assert Scheduler(owner).detect_conflicts() == []


# --------------------------------------------------------------------------
# Happy paths — the planner behaving as designed
# --------------------------------------------------------------------------


def _owner_with_tasks(minutes, *tasks):
    """Build an owner with a single pet holding the given tasks."""
    owner = Owner(name="Jordan", minutes_available=minutes)
    pet = Pet(name="Mochi", species="dog")
    for task in tasks:
        pet.add_task(task)
    owner.add_pet(pet)
    return owner


def test_build_plan_keeps_high_priority_within_budget():
    """With a tight budget, higher-priority tasks make the plan and low drops."""
    owner = _owner_with_tasks(
        50,
        Task("Walk", 30, Priority.HIGH, time="07:00"),
        Task("Play", 20, Priority.MEDIUM, time="08:00"),
        Task("Brush", 20, Priority.LOW, time="09:00"),
    )

    plan = Scheduler(owner).build_plan()

    titles = [item.task.title for item in plan]
    assert titles == ["Walk", "Play"]  # 30 + 20 = 50 min; Brush dropped


def test_build_plan_places_tasks_at_their_own_times():
    """Each surviving task lands at its own 'time', ordered chronologically."""
    owner = _owner_with_tasks(
        120,
        Task("Evening walk", 30, Priority.HIGH, time="18:00"),
        Task("Morning feed", 15, Priority.HIGH, time="07:00"),
    )

    plan = Scheduler(owner).build_plan()

    assert [item.start.strftime("%H:%M") for item in plan] == ["07:00", "18:00"]


def test_resolve_conflicts_pushes_back_overlapping_slot():
    """Two overlapping tasks are bumped so their slots no longer collide."""
    owner = _owner_with_tasks(
        120,
        Task("Vet call", 30, Priority.HIGH, time="09:00"),
        Task("Grooming", 20, Priority.HIGH, time="09:15"),
    )

    plan = Scheduler(owner).build_plan()

    # First runs 09:00–09:30, so the second is pushed to start at 09:30.
    assert plan[0].start.strftime("%H:%M") == "09:00"
    assert plan[1].start.strftime("%H:%M") == "09:30"


# --------------------------------------------------------------------------
# Edge cases — unusual-but-valid input the code handles correctly today
# --------------------------------------------------------------------------


def test_owner_with_no_pets_produces_no_plan():
    """No pets → no tasks → an explanatory, non-crashing message."""
    scheduler = Scheduler(Owner(name="Jordan", minutes_available=60))

    assert scheduler.build_plan() == []
    assert scheduler.explain_plan() == (
        "No plan: no pending tasks, or no time available."
    )


def test_pet_with_no_tasks_contributes_nothing():
    """A pet that owns no tasks does not affect aggregation or planning."""
    owner = Owner(name="Jordan", minutes_available=60)
    owner.add_pet(Pet(name="Mochi", species="dog"))

    assert owner.all_tasks() == []
    assert Scheduler(owner).build_plan() == []


def test_zero_budget_drops_everything():
    """With zero minutes available, even valid tasks are all filtered out."""
    owner = _owner_with_tasks(0, Task("Walk", 30, Priority.HIGH, time="07:00"))

    assert Scheduler(owner).build_plan() == []


def test_task_longer_than_budget_is_dropped():
    """A single task that exceeds the whole budget never makes the plan."""
    owner = _owner_with_tasks(20, Task("Long hike", 90, Priority.HIGH, time="07:00"))

    assert Scheduler(owner).build_plan() == []


def test_greedy_budget_skips_big_task_and_keeps_smaller_later_one():
    """The greedy filter drops an unaffordable high task but keeps a smaller
    lower one that still fits the remaining budget."""
    owner = _owner_with_tasks(
        30,
        Task("Big walk", 45, Priority.HIGH, time="07:00"),
        Task("Quick feed", 20, Priority.MEDIUM, time="08:00"),
    )

    plan = Scheduler(owner).build_plan()

    assert [item.task.title for item in plan] == ["Quick feed"]


def test_next_occurrence_on_one_off_task_raises():
    """Advancing a non-recurring task is a programming error, not a silent no-op."""
    with pytest.raises(ValueError):
        Task("Morning walk", 30, Priority.HIGH).next_occurrence()


def test_sort_by_time_places_untimed_tasks_first():
    """Tasks with no time ('') sort ahead of any 'HH:MM' task."""
    owner = _owner_with_tasks(
        120,
        Task("Timed", 10, Priority.LOW, time="08:00"),
        Task("Untimed", 10, Priority.LOW),
    )

    ordered = Scheduler(owner).sort_by_time()

    assert [t.title for t in ordered] == ["Untimed", "Timed"]


def test_detect_conflicts_ignores_done_and_untimed_tasks():
    """Completed tasks and tasks with no time never trigger a conflict warning."""
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="dog")
    owner.add_pet(pet)
    done = Task("Done task", 15, Priority.HIGH, time="10:00", done=True)
    pending = Task("Pending task", 15, Priority.HIGH, time="10:00")
    untimed = Task("No time", 15, Priority.HIGH)
    for t in (done, pending, untimed):
        pet.add_task(t)

    # Only one *pending, timed* task at 10:00, so nothing collides.
    assert Scheduler(owner).detect_conflicts() == []


def test_sort_diverges_on_done_filtering():
    """sort_by_priority drops done tasks; sort_by_time keeps them. This pins
    the intentional (and easy-to-break) divergence between the two sorts."""
    owner = _owner_with_tasks(
        120,
        Task("Done", 10, Priority.HIGH, time="07:00", done=True),
        Task("Pending", 10, Priority.LOW, time="08:00"),
    )
    scheduler = Scheduler(owner)

    assert [t.title for t in scheduler.sort_by_priority()] == ["Pending"]
    assert {t.title for t in scheduler.sort_by_time()} == {"Done", "Pending"}


# --------------------------------------------------------------------------
# Bug-exposing cases — assert the *correct* behavior, marked xfail so the
# suite stays green while documenting each known defect. Flip to a passing
# test (drop the xfail) once the underlying bug is fixed.
# --------------------------------------------------------------------------


def test_recompleting_recurring_task_should_not_duplicate_followup():
    pet = Pet(name="Biscuit", species="cat")
    feeding = Task("Feeding", 10, Priority.HIGH, frequency="daily")
    pet.add_task(feeding)

    pet.mark_task_complete(feeding)  # -> 2 tasks (original + follow-up)
    pet.mark_task_complete(feeding)  # completing an already-done task again

    # Expected: no second follow-up. Actual today: a third task appears.
    assert len(pet.tasks) == 2


def test_late_night_task_end_should_not_wrap_before_start():
    owner = _owner_with_tasks(
        120, Task("Late walk", 60, Priority.HIGH, time="23:30")
    )

    plan = Scheduler(owner).build_plan()

    assert plan[0].end > plan[0].start


def test_non_zero_padded_time_sorts_chronologically():
    owner = _owner_with_tasks(
        120,
        Task("Ten", 10, Priority.LOW, time="10:00"),
        Task("Nine", 10, Priority.LOW, time="9:00"),
    )

    ordered = Scheduler(owner).sort_by_time()

    assert [t.title for t in ordered] == ["Nine", "Ten"]


def test_detect_conflicts_flags_equivalent_but_differently_formatted_times():
    owner = Owner(name="Jordan")
    pet = Pet(name="Mochi", species="dog")
    owner.add_pet(pet)
    pet.add_task(Task("A", 15, Priority.HIGH, time="09:00"))
    pet.add_task(Task("B", 15, Priority.HIGH, time="9:00"))

    assert len(Scheduler(owner).detect_conflicts()) == 1


def test_frequency_is_case_insensitive():
    pet = Pet(name="Mochi", species="dog")
    feeding = Task("Feeding", 10, Priority.HIGH, frequency="Daily")
    pet.add_task(feeding)

    follow_up = pet.mark_task_complete(feeding)

    assert follow_up is not None


def test_tomorrows_followup_should_not_appear_in_todays_plan():
    pet = Pet(name="Biscuit", species="cat")
    owner = Owner(name="Jordan", minutes_available=60)
    owner.add_pet(pet)
    feeding = Task("Feeding", 10, Priority.HIGH, time="08:00", frequency="daily")
    pet.add_task(feeding)

    pet.mark_task_complete(feeding)  # original done; follow-up due tomorrow
    plan = Scheduler(owner).build_plan()

    # Only the (now-done) original was for today; tomorrow's copy shouldn't show.
    assert plan == []


# --------------------------------------------------------------------------
# Coverage completions — closing the two remaining gaps
# --------------------------------------------------------------------------


def test_sort_by_priority_orders_high_to_low():
    """sort_by_priority() returns pending tasks strictly HIGH -> MED -> LOW,
    regardless of the order they were added."""
    owner = _owner_with_tasks(
        120,
        Task("Low chore", 10, Priority.LOW),
        Task("High chore", 10, Priority.HIGH),
        Task("Medium chore", 10, Priority.MEDIUM),
    )

    ordered = Scheduler(owner).sort_by_priority()

    assert [t.priority for t in ordered] == [
        Priority.HIGH,
        Priority.MEDIUM,
        Priority.LOW,
    ]


def test_tight_budget_keeps_only_highest_priority_of_equal_length_tasks():
    """40 minutes, three 30-min tasks: only one fits, and priority decides
    which — the HIGH task survives; MEDIUM and LOW are dropped."""
    owner = _owner_with_tasks(
        40,
        Task("Med walk", 30, Priority.MEDIUM, time="08:00"),
        Task("Low groom", 30, Priority.LOW, time="09:00"),
        Task("High feed", 30, Priority.HIGH, time="07:00"),
    )

    plan = Scheduler(owner).build_plan()

    assert [item.task.title for item in plan] == ["High feed"]


def test_built_plan_has_no_overlapping_slots():
    """Whatever the requested times, the final plan never double-books: no two
    ScheduledTask slots overlap. Uses several tasks clustered around one time."""
    owner = _owner_with_tasks(
        300,
        Task("A", 30, Priority.HIGH, time="12:00"),
        Task("B", 30, Priority.HIGH, time="12:15"),
        Task("C", 30, Priority.HIGH, time="12:00"),
        Task("D", 20, Priority.HIGH, time="12:45"),
    )

    plan = Scheduler(owner).build_plan()

    assert len(plan) == 4  # all fit within the 300-min budget
    for earlier, later in zip(plan, plan[1:]):
        assert not earlier.overlaps(later)
        assert later.start >= earlier.end

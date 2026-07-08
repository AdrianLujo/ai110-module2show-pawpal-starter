"""Tests for core PawPal+ behaviors."""

import os
import sys
from datetime import date, timedelta

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

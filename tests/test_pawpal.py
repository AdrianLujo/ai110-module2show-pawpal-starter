"""Tests for core PawPal+ behaviors."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pawpal_system import Pet, Task, Priority


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

"""Testing ground for PawPal+ logic.

Run with: python main.py
Builds a sample owner, pets, and tasks, then prints today's schedule.
"""

from pawpal_system import Owner, Pet, Task, Scheduler, Priority


def main() -> None:
    # Owner with a daily time budget.
    owner = Owner(name="Jordan")
    owner.set_availability(90)

    # At least two pets.
    dog = Pet(name="Mochi", species="dog")
    cat = Pet(name="Biscuit", species="cat")
    owner.add_pet(dog)
    owner.add_pet(cat)

    # Tasks added out of chronological order on purpose, so sort_by_time()
    # has something real to reorder.
    dog.add_task(Task("Grooming", 45, Priority.LOW, time="16:30"))
    dog.add_task(Task("Morning walk", 30, Priority.HIGH, time="07:00"))
    cat.add_task(Task("Playtime", 20, Priority.MEDIUM, time="12:15"))
    cat.add_task(Task("Feeding", 10, Priority.HIGH, time="06:45", frequency="daily"))

    # Deliberate clash: the dog's vet call lands at 12:15, same as the cat's
    # playtime above — a conflict across two different pets.
    dog.add_task(Task("Vet call", 15, Priority.HIGH, time="12:15"))

    # Completing a recurring task auto-spawns its next occurrence.
    feeding = cat.tasks[-1]
    follow_up = cat.mark_task_complete(feeding)
    print("Recurring task")
    print("=" * 40)
    print(f"  Completed: {feeding.title} ({feeding.frequency})")
    if follow_up is not None:
        print(f"  Auto-created next: {follow_up.title} due {follow_up.due_date}")
    print()

    scheduler = Scheduler(owner)

    # Conflict detection: warn (don't crash) when tasks share a time slot.
    print("Schedule conflicts")
    print("=" * 40)
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            print(f"  {warning}")
    else:
        print("  No conflicts detected.")
    print()

    print("Today's Schedule")
    print("=" * 40)
    print(scheduler.explain_plan())

    # Sorting: tasks were added out of order — sort_by_time() fixes that.
    print("\nAll tasks sorted by time")
    print("=" * 40)
    for task in scheduler.sort_by_time():
        status = "done" if task.done else "pending"
        print(f"  {task.time} — {task.title} ({status})")

    # Filtering by completion status.
    print("\nPending tasks only")
    print("=" * 40)
    for task in scheduler.filter_tasks(done=False):
        print(f"  {task.time} — {task.title}")

    # Filtering by pet name.
    print("\nTasks for Mochi only")
    print("=" * 40)
    for task in scheduler.filter_tasks(pet_name="Mochi"):
        print(f"  {task.time} — {task.title}")


if __name__ == "__main__":
    main()

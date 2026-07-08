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

    # At least three tasks with different durations and priorities.
    dog.add_task(Task("Morning walk", 30, Priority.HIGH))
    dog.add_task(Task("Grooming", 45, Priority.LOW))
    cat.add_task(Task("Feeding", 10, Priority.HIGH))
    cat.add_task(Task("Playtime", 20, Priority.MEDIUM))

    # Build and print today's schedule.
    scheduler = Scheduler(owner)
    print("Today's Schedule")
    print("=" * 40)
    print(scheduler.explain_plan())


if __name__ == "__main__":
    main()

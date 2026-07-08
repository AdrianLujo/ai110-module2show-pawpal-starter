# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**
- Add a pet
- Schedule a walk
- See today's tasks
- Briefly describe your initial UML design.
The UML has 4 classes: Owner, Pet, Task, & Scheduler. The Owner owns pets, the pet has tasks, the scheduler plans for owners by scheduling tasks for pets. In this sense, the tasks belong to the pet despite the owner completing them.

    Owner "1" --> "*" Pet : owns
    Pet "1" --> "*" Task : has
    Scheduler --> Owner : plans for
    Scheduler --> Pet : schedules
    Scheduler ..> Task : orders
- What classes did you include, and what responsibilities did you assign to each?
Owner: Owner has pets
Pet: Pet has Tasks
Task: A thing to do for a Pet
Scheduler: Arranges Pet related Tasks for the Owner

**b. Design changes**

- Did your design change during implementation?
Yes
- If yes, describe at least one change and why you made it.

On recommendation from Claude, we added a ScheduledTask class that pairs a task with a start and end time, since a original task only stores the duration and not when it occurs. This lets the plan show actual times and compare tasks for overlaps.

We also changed Task.priority from a string to a Priority enum (LOW, MEDIUM, HIGH) and removed the separate priority_score() method.

We also removed the scheduler's own task list so the pet's task list is the single source of truth, and changed filter_by_time() to read the owner's available minutes instead of taking it as an argument. We made the scheduler work across all of the owner's pets: the owner exposes an all_tasks() method that flattens every pet's tasks, and the scheduler reads through that instead of taking a single pet. We also added a day_start time to the scheduler and a done flag to Task so completed tasks are skipped when planning.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

Priority, time budget, and each task's set time. It sorts by priority (HIGH to LOW). Then filter_by_time() keeps tasks until the owner's available minutes run out, so low priority tasks get dropped if there isn't room. After that it places tasks at their "HH:MM" and pushes back overlaps. Done tasks are skipped.

- How did you decide which constraints mattered most?

Priority came first since the important tasks like feeding should always happen. Time is the what decides what fits in the schedule. The set time lays out the day in order.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.

Our conflict warning only checks for exact time matches. detect_conflicts() groups tasks by their "HH:MM" string, so it only warns when two tasks start at the exact same time. It doesn't look at durations, so a 30 min task at 12:00 and a task at 12:15 overlap but won't get flagged. We did it this way to keep it simple and so it can't crash on a bad time value.

- Why is that tradeoff reasonable for this scenario?

For a pet care planner people mostly enter tasks at round times like 6:45 or 7:00, so same time clashes matter. The plan still handles overlaps: resolve_conflicts() uses each task's duration to push slots back so there is no double booking. The warning stays simple while the schedule comes out with no overlaps.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

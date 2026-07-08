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

The conflict warning only checks for exact time matches. detect_conflicts() groups tasks by the "HH:MM" string, so it only warns when two tasks start at the exact same time. It doesn't look at durations, so a 30 min task at 12:00 and a task at 12:15 overlap but won't get flagged. This was done in this way to keep it simple and so the program doesn't crash on a bad time value.

- Why is that tradeoff reasonable for this scenario?

For a pet care planner people mostly enter tasks at round times like 6:45 or 7:00, so same time clashes matter. The plan still handles overlaps: resolve_conflicts() uses each task's duration to push slots back so there is no double booking. The warning stays simple while the schedule comes out with no overlaps.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?

I used Claude Code for brainstorming the UML, turning it into class stubs, filling in the scheduling logic, writing tests, and the README. It was most useful for refactors.

- Which AI coding assistant features were most effective for building your scheduler?

TThe most effective feature is that Claude can read the whole repo. Since Claude had all our files in context, Claude's code recommendations actually fit our design. It knew that the pet owns the tasks. Claude could also run the tests, main.py, and read the output, so we could verify changes as we went along. 

- What kinds of prompts or questions were most helpful?

Asking about specific situationsnlike "what happens if two tasks start at the same time on different pets?" generated code that could be tested. Asking it to explain why before writing it also helped, because I could decide if the idea matched the intended design.

- How did using separate chat sessions for different phases help you stay organized?

One session per phase: design, wiring the UI, the scheduling logic, then tests and docs. That matches how our commits are grouped. Keeping them apart meant each one stayed on topic. The design session didn't get mixed up with Streamlit details, and the testing session wasn't reopening design arguments we already settled. It was also easier to go back and find why we did something, and one giant thread didn't fill up with old context that confused later answers.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is. / Give one example of an AI suggestion you rejected or modified to keep your system design clean.

For conflict handling the suggestion was one method that both detected and fixed overlaps using durations. We split it into two instead. detect_conflicts() just warns when two tasks share the exact same start time, and it can't crash on a bad time string. resolve_conflicts() does the actual duration based push-back in build_plan(). One method that both warned the user and changed the plan was harder to test. I also didn't keep a task list on the Scheduler like it first set up, Claude suggested making the pet's task list the only source of truth so two lists couldn't get out of sync.

- How did you evaluate or verify what the AI suggested?

Suggestions got a test in pytest, and for the tricky ones we wrote the test first and checked the code against it. 

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

We have 28 tests in tests/test_pawpal.py. They cover the time budget, priority ordering, sorting by time, recurrence, conflict detection, and overlap resolution. There are also tests for empty owners and pets, the midnight bug, and a task due tomorrow staying out of today's plan.

- Why were these tests important?

A lot of them are for bugs we that were found. Tests also let us change code without worrying, since anything we broke would show up right away.

**b. Confidence**

- How confident are you that your scheduler works correctly?

Pretty confident, about a 4 out of 5. All the tests pass and they cover the main behaviors plus the edge cases we found. It's not a 5 because the tests are only on the classes. We didn't test the Streamlit UI.

- What edge cases would you test next if you had more time?

Aa task that exactly fills the budget or a lot of tasks at once.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

Keeping the design simple. The pet's task list is the only source of truth, each class does one thing, and the conflict warning is separate from actually fixing overlaps.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

I'd handle tasks that cross midnight properly, and add UI tests.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

Getting the design right first made coding easier. Once we had one source of truth and clear jobs for each class, the AI's code fit right in and the tests were simple to write.
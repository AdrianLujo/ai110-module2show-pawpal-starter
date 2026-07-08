import streamlit as st

from pawpal_system import Owner, Pet, Task, Scheduler, Priority

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

PRIORITY_MAP = {"low": Priority.LOW, "medium": Priority.MEDIUM, "high": Priority.HIGH}

# Create the Owner (and its Pet) once, then reuse it across reruns.
# Without this check, every widget interaction would rebuild the Owner and
# wipe out the tasks the user already added.
if "owner" not in st.session_state:
    owner = Owner(name="Jordan")
    owner.add_pet(Pet(name="Mochi", species="dog"))
    st.session_state.owner = owner

owner = st.session_state.owner

st.subheader("Owner")
owner.name = st.text_input("Owner name", value=owner.name)
owner.minutes_available = st.number_input(
    "Minutes available today", min_value=0, max_value=1440, value=owner.minutes_available or 90
)

def add_pet_from_form():
    """Callback: register the new pet, then select it and clear the form.

    Runs before the rerun's main body, so state is settled by the time the
    widgets below are drawn.
    """
    name = st.session_state.new_pet_name.strip()
    if not name:
        st.session_state.pet_warning = "Give the pet a name before adding it."
        return
    owner.add_pet(Pet(name=name, species=st.session_state.new_pet_species))
    st.session_state.active_pet_index = len(owner.pets) - 1  # auto-select it
    st.session_state.new_pet_name = ""  # clear the input
    st.session_state.pet_warning = ""

st.subheader("Add a Pet")
new_pet_col1, new_pet_col2 = st.columns(2)
with new_pet_col1:
    st.text_input("New pet name", key="new_pet_name")
with new_pet_col2:
    st.selectbox("New pet species", ["dog", "cat", "other"], key="new_pet_species")

st.button("Add pet", on_click=add_pet_from_form)

if st.session_state.get("pet_warning"):
    st.warning(st.session_state.pet_warning)

# Choose which pet to add tasks to (defaults to the most recently added).
pet_names = [p.name for p in owner.pets]
pet_index = st.selectbox(
    "Active pet", range(len(pet_names)), format_func=lambda i: pet_names[i],
    key="active_pet_index",
)
pet = owner.pets[pet_index]

st.markdown(f"### Tasks for {pet.name}")
st.caption("Add tasks below. They persist across reruns because the Owner lives in session_state.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
with col4:
    task_time = st.text_input(
        "Time (HH:MM)", value="08:00",
        help="Preferred start time, 24-hour. Leave blank for no fixed time.",
    )

if st.button("Add task"):
    pet.add_task(
        Task(task_title, int(duration), PRIORITY_MAP[priority], time=task_time.strip())
    )

if pet.tasks:
    st.write("Current tasks:")
    st.table(
        [
            {
                "title": t.title,
                "time": t.time or "—",
                "duration_minutes": t.duration_minutes,
                "priority": t.priority.name.lower(),
                "done": t.done,
            }
            for t in pet.tasks
        ]
    )
else:
    st.info("No tasks yet. Add one above.")

st.divider()

# One Scheduler drives every view below: the sorted/filtered table, the
# conflict check, and the generated plan all read through the same object.
scheduler = Scheduler(owner)

st.subheader("All Tasks (across pets)")
st.caption("Sort and filter every task the owner has, using the Scheduler.")

sort_col, filter_col = st.columns(2)
with sort_col:
    sort_by = st.radio("Sort by", ["priority", "time"], horizontal=True)
with filter_col:
    status = st.radio("Show", ["all", "pending", "completed"], horizontal=True)

# Choose the ordering from the Scheduler, then narrow to the requested status.
if sort_by == "priority":
    ordered = scheduler.sort_by_priority()
else:
    ordered = scheduler.sort_by_time()
done_flag = {"all": None, "pending": False, "completed": True}[status]
visible = scheduler.filter_tasks(done=done_flag)
# Keep the sorted order, but only rows that survive the status filter.
rows = [t for t in ordered if t in visible]

# Map each task back to the pet it belongs to, for a clearer table.
pet_of = {id(t): p.name for p in owner.pets for t in p.tasks}

if rows:
    st.table(
        [
            {
                "pet": pet_of.get(id(t), "—"),
                "title": t.title,
                "time": t.time or "—",
                "duration_minutes": t.duration_minutes,
                "priority": t.priority.name.lower(),
                "done": t.done,
            }
            for t in rows
        ]
    )
else:
    st.info("No tasks match this filter.")

st.divider()

st.subheader("Conflict Check")
st.caption("Flags tasks that are scheduled at the same start time.")

conflicts = scheduler.detect_conflicts()
if conflicts:
    st.warning(
        f"⚠️ {len(conflicts)} scheduling conflict(s) found — "
        "you can't be in two places at once:"
    )
    for warning in conflicts:
        # Strip the "WARNING: " prefix; the icon already signals severity.
        message = warning.removeprefix("WARNING: ")
        st.warning(message, icon="🕑")
    st.info(
        "Tip: give one of the clashing tasks a different start time "
        "to resolve the overlap."
    )
else:
    st.success(
        "✅ No scheduling conflicts — every task starts at a distinct time."
    )

st.divider()

st.subheader("Build Schedule")
st.caption("Runs the Scheduler over the owner's pets and shows today's plan.")

if st.button("Generate schedule"):
    plan = scheduler.build_plan()
    if not plan:
        st.warning("No plan: add tasks and make sure minutes available is more than 0.")
    else:
        st.success(f"Planned {len(plan)} task(s) for {owner.name} today.")
        st.table(
            [
                {
                    "start": item.start.strftime("%H:%M"),
                    "end": item.end.strftime("%H:%M"),
                    "task": item.task.title,
                    "duration_minutes": item.task.duration_minutes,
                    "priority": item.task.priority.name.lower(),
                }
                for item in plan
            ]
        )
        with st.expander("Why this plan?"):
            st.text(scheduler.explain_plan())

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

col1, col2, col3 = st.columns(3)
with col1:
    task_title = st.text_input("Task title", value="Morning walk")
with col2:
    duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
with col3:
    priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

if st.button("Add task"):
    pet.add_task(Task(task_title, int(duration), PRIORITY_MAP[priority]))

if pet.tasks:
    st.write("Current tasks:")
    st.table(
        [
            {
                "title": t.title,
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

st.subheader("Build Schedule")
st.caption("Runs the Scheduler over the owner's pets and shows today's plan.")

if st.button("Generate schedule"):
    scheduler = Scheduler(owner)
    plan = scheduler.build_plan()
    if not plan:
        st.warning("No plan: add tasks and make sure minutes available is more than 0.")
    else:
        st.text(scheduler.explain_plan())

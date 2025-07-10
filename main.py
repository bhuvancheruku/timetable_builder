import streamlit as st
import pandas as pd
from datetime import datetime
from modules.timetable_logic import GeneticAlgorithm, export_to_pdf

st.title("Academic Timetable Generator")

branch_name = st.text_input("Branch Name")

# --- Time Settings ---
st.write("College Start Time")
start_time = st.time_input("Start Time", value=datetime.strptime("09:00", "%H:%M").time())

st.write("College End Time")
end_time = st.time_input("End Time", value=datetime.strptime("17:00", "%H:%M").time())

# --- General Inputs ---
num_sections = st.number_input("Number of Sections", min_value=1, value=1)
num_classes = st.number_input("Number of Classes per Day", min_value=1, value=5)

# --- Breaks ---
breaks = []
if st.checkbox("Add Morning Break"):
    morning_break_time = st.time_input("Morning Break Time", value=datetime.strptime("11:00", "%H:%M").time())
    morning_break_duration = st.number_input("Morning Break Duration (minutes)", min_value=1, value=10)
    breaks.append((morning_break_time, morning_break_duration))

if st.checkbox("Add Lunch Break"):
    lunch_break_time = st.time_input("Lunch Break Time", value=datetime.strptime("13:00", "%H:%M").time())
    lunch_break_duration = st.number_input("Lunch Break Duration (minutes)", min_value=1, value=60)
    breaks.append((lunch_break_time, lunch_break_duration))

# --- Subjects and Faculty ---
num_subjects = st.number_input("Number of Subjects", min_value=1, value=5)
subjects = []
faculty_members = {}

for i in range(num_subjects):
    subject = st.text_input(f"Subject {i + 1}")
    if subject:
        subjects.append(subject)
        num_faculty = st.number_input(f"Number of Faculty for {subject}", min_value=1, value=1, key=f"faculty_count_{i}")
        faculty = [st.text_input(f"Faculty {j + 1} for {subject}", key=f"faculty_{i}_{j}") for j in range(num_faculty)]
        faculty_members[subject] = faculty

# --- Timetable Generation ---
def generate_timetable_with_ga():
    ga = GeneticAlgorithm(subjects, faculty_members, breaks, num_classes, num_sections, start_time, end_time)
    return ga.optimize()

if st.button("Generate Timetable"):
    if not branch_name:
        st.warning("Please provide a branch name.")
    elif not subjects:
        st.warning("Please provide at least one subject.")
    elif not all(faculty_members.get(sub) for sub in subjects):
        st.warning("Please ensure all subjects have at least one faculty member.")
    else:
        timetable_data = generate_timetable_with_ga()
        flat_timetable_df = pd.DataFrame([
            {
                "Branch": branch_name,
                "Section": section,
                "Day": day,
                "Time Slot": f"{time_slot[0]} - {time_slot[1]}" if time_slot[1] != "BREAK" else "BREAK",
                "Subject": subject,
                "Faculty": faculty
            }
            for section, days in timetable_data.items()
            for day, classes in days.items()
            for time_slot, subject, faculty in classes
        ])
        st.session_state.timetable_data = timetable_data
        st.session_state.flat_timetable_df = flat_timetable_df
        st.write("### Timetable")
        st.dataframe(flat_timetable_df)

# --- Export to PDF ---
if 'flat_timetable_df' in st.session_state:
    if st.button("Export to PDF"):
        time_slots = [(slot[0], slot[1]) for slot in st.session_state.timetable_data[list(st.session_state.timetable_data.keys())[0]]["Monday"]]
        pdf_buffer = export_to_pdf(st.session_state.timetable_data, time_slots, branch_name)
        st.download_button("Download Timetable PDF", data=pdf_buffer, file_name=f"{branch_name}_timetable.pdf", mime="application/pdf")

import streamlit as st
import pandas as pd
from datetime import datetime
from modules.timetable_logic import GeneticAlgorithm, export_to_pdf

st.set_page_config(page_title="Universal Timetable Builder", layout="wide")

st.title("Universal Academic Timetable Builder")
st.markdown("Generate conflict-free, printable timetables tailored to your institution's format.")

def custom_time_input(label, default_hour, default_min, default_ampm, key_prefix):
    st.write(f"**{label}**")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        hour = st.selectbox("Hour", options=list(range(1, 13)), index=default_hour-1, key=f"{key_prefix}_h")
    with c2:
        minute = st.selectbox("Min", options=[f"{m:02d}" for m in range(0, 60, 5)], index=int(default_min/5), key=f"{key_prefix}_m")
    with c3:
        am_pm = st.selectbox("AM/PM", options=["AM", "PM"], index=0 if default_ampm == "AM" else 1, key=f"{key_prefix}_ap")
    
    h_24 = hour
    if am_pm == "PM" and hour != 12: h_24 += 12
    elif am_pm == "AM" and hour == 12: h_24 = 0
    return datetime.strptime(f"{h_24}:{minute}", "%H:%M").time()

# --- SIDEBAR: GLOBAL CONFIGURATION ---
with st.sidebar:
    st.header("1. Report Configuration")
    org_name = st.text_input("Institution Name", value="MALLA REDDY UNIVERSITY")
    subtitle = st.text_area("Address / Subtitle", value="Maisammaguda, Hyderabad, Telangana State.")
    dept_name = st.text_input("Department Name", value="DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING")
    academic_label = st.text_input("Academic Label", value="IV Year B. Tech-II Sem Time Table 2024-25")
    uploaded_logo = st.file_uploader("Upload Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])

# --- MAIN FORM ---
st.header("2. Schedule Parameters")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Time Settings")
    start_time = custom_time_input("College Start Time", 9, 0, "AM", "start")
    end_time = custom_time_input("College End Time", 4, 0, "PM", "end")
    
    # --- DURATION MODE TOGGLE ---
    st.markdown("---")
    use_fixed = st.checkbox("Use Fixed Class Duration?", value=True, help="If checked, classes will be exactly X minutes. If unchecked, time is divided equally.")
    
    if use_fixed:
        fixed_duration = st.number_input("Class Duration (Minutes)", min_value=30, value=60, step=5)
        duration_mode = "fixed"
    else:
        duration_mode = "auto"
        fixed_duration = 60
        
    num_classes = st.number_input("Max Classes per Day", min_value=1, value=6)

with col2:
    st.subheader("Structure")
    num_sections = st.number_input("Number of Sections", min_value=1, value=2)
    branch_name = st.text_input("Branch Code (e.g., CSE)", value="CSE")

# --- BREAKS ---
st.subheader("Breaks")
breaks = []
if st.checkbox("Add Morning Break"):
    c1, c2 = st.columns(2)
    with c1: mb_time = custom_time_input("Start Time", 11, 0, "AM", "mb")
    with c2: 
        st.write("**Duration**")
        mb_dur = st.number_input("Minutes", min_value=5, value=10, key="mb_dur")
    breaks.append((mb_time, mb_dur))

if st.checkbox("Add Lunch Break"):
    c1, c2 = st.columns(2)
    with c1: lb_time = custom_time_input("Start Time", 1, 0, "PM", "lb")
    with c2: 
        st.write("**Duration**")
        lb_dur = st.number_input("Minutes", min_value=15, value=60, key="lb_dur")
    breaks.append((lb_time, lb_dur))

# --- SUBJECTS & FACULTY ---
st.header("3. Subjects & Faculty")
if 'subjects_list' not in st.session_state:
    st.session_state.subjects_list = []

with st.expander("Manage Subjects", expanded=True):
    num_subs = st.number_input("How many subjects?", min_value=1, value=5)
    subjects_data = [] 
    faculty_map = {}   
    
    for i in range(num_subs):
        st.markdown(f"**Subject {i+1}**")
        c1, c2, c3 = st.columns([2, 1, 1])
        s_name = c1.text_input(f"Subject Name", key=f"sname_{i}")
        s_acro = c2.text_input(f"Acronym", key=f"sacro_{i}")
        s_code = c3.text_input(f"Code", key=f"scode_{i}")
        fac_input = st.text_input(f"Faculty (comma separated)", key=f"fac_{i}")
        
        if s_name:
            fac_list = [f.strip() for f in fac_input.split(',')] if fac_input else []
            subjects_data.append({
                "name": s_name,
                "acronym": s_acro if s_acro else s_name[:3].upper(),
                "code": s_code
            })
            faculty_map[s_name] = fac_list

# --- GENERATION ---
if st.button("Generate Timetable", type="primary"):
    valid = True
    for sub in subjects_data:
        if not faculty_map.get(sub['name']):
            st.error(f"Subject '{sub['name']}' has no faculty assigned!")
            valid = False
            
    if valid:
        ga = GeneticAlgorithm(subjects_data, faculty_map, breaks, num_classes, num_sections, start_time, end_time, duration_mode, fixed_duration)
        with st.spinner("Optimizing schedule..."):
            best_schedule = ga.optimize()
            st.session_state.timetable_data = best_schedule
            st.session_state.generated = True
            st.success("Timetable Generated Successfully!")

# --- EXPORT ---
if st.session_state.get('generated'):
    st.divider()
    st.header("4. Finalize & Export")
    
    st.subheader("Section Details")
    section_details = {}
    cols = st.columns(min(num_sections, 3))
    
    for i in range(1, num_sections + 1):
        sec_name = f"Section {i}"
        with cols[(i-1) % 3]:
            st.markdown(f"**{sec_name}**")
            room = st.text_input(f"Room No", key=f"room_{i}")
            in_charge = st.text_input(f"Class In-Charge", key=f"ic_{i}")
            section_details[sec_name] = {'room': room, 'in_charge': in_charge}

    if st.button("Download PDF Report"):
        pdf_config = {
            'org_name': org_name,
            'subtitle': subtitle,
            'dept_name': dept_name,
            'academic_label': academic_label,
            'logo_bytes': uploaded_logo
        }
        first_sec = list(st.session_state.timetable_data.keys())[0]
        raw_slots = [x[0] for x in st.session_state.timetable_data[first_sec]["Monday"]]
        
        pdf_file = export_to_pdf(st.session_state.timetable_data, raw_slots, pdf_config, section_details)
        
        st.download_button(
            label="Download PDF",
            data=pdf_file,
            file_name=f"{branch_name}_Timetable.pdf",
            mime="application/pdf"
        )

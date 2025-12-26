import streamlit as st
import pandas as pd
from datetime import datetime
from modules.timetable_logic import GeneticAlgorithm, export_to_pdf

st.set_page_config(page_title="Universal Timetable Builder", layout="wide")

st.title("Universal Academic Timetable Builder")
st.markdown("Generate conflict-free, printable timetables tailored to your institution's format.")

# --- SIDEBAR: GLOBAL CONFIGURATION ---
with st.sidebar:
    st.header("1. Report Configuration")
    st.info("Customize the look of your PDF.")
    
    org_name = st.text_input("Institution Name", value="MALLA REDDY UNIVERSITY")
    subtitle = st.text_area("Address / Subtitle", value="Maisammaguda, Hyderabad, Telangana State.")
    dept_name = st.text_input("Department Name", value="DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING")
    academic_label = st.text_input("Academic Label", value="IV Year B. Tech-II Sem Time Table 2024-25")
    
    uploaded_logo = st.file_uploader("Upload Logo (PNG/JPG)", type=["png", "jpg", "jpeg"])

# --- MAIN FORM ---
st.header("2. Schedule Parameters")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Time Settings (12-Hour Format)")
    # Note: Streamlit time_input returns 24h datetime.time, but the UI allows 12h selection if system locale supports it, 
    # or we handle the logic. We will rely on standard input but label it clearly.
    start_time = st.time_input("College Start Time", value=datetime.strptime("09:00", "%H:%M").time())
    end_time = st.time_input("College End Time", value=datetime.strptime("16:00", "%H:%M").time())
    
    num_classes = st.number_input("Classes per Day", min_value=1, value=6)

with col2:
    st.subheader("Structure")
    num_sections = st.number_input("Number of Sections", min_value=1, value=2)
    branch_name = st.text_input("Branch Code (e.g., CSE)", value="CSE")

# --- BREAKS ---
st.subheader("Breaks")
breaks = []
if st.checkbox("Add Morning Break"):
    c1, c2 = st.columns(2)
    mb_time = c1.time_input("Morning Break Start", value=datetime.strptime("11:00", "%H:%M").time())
    mb_dur = c2.number_input("Duration (mins)", min_value=5, value=10, key="mb_dur")
    breaks.append((mb_time, mb_dur))

if st.checkbox("Add Lunch Break", value=True):
    c1, c2 = st.columns(2)
    lb_time = c1.time_input("Lunch Start", value=datetime.strptime("13:00", "%H:%M").time())
    lb_dur = c2.number_input("Duration (mins)", min_value=15, value=60, key="lb_dur")
    breaks.append((lb_time, lb_dur))

# --- SUBJECTS & FACULTY ---
st.header("3. Subjects & Faculty")
st.markdown("Add subjects. **Acronym** appears in the grid. **Subject Name** & **Code** appear in the footer.")

if 'subjects_list' not in st.session_state:
    st.session_state.subjects_list = []

# Simple Form to Add Subjects
with st.expander("Manage Subjects", expanded=True):
    num_subs = st.number_input("How many subjects?", min_value=1, value=5)
    
    subjects_data = [] # List of dicts
    faculty_map = {}   # { SubjectName: [Faculty1, Faculty2] }
    
    for i in range(num_subs):
        st.markdown(f"**Subject {i+1}**")
        c1, c2, c3 = st.columns([2, 1, 1])
        s_name = c1.text_input(f"Subject Name {i+1}", key=f"sname_{i}")
        s_acro = c2.text_input(f"Acronym {i+1}", help="Short text for the box (e.g. SIE)", key=f"sacro_{i}")
        s_code = c3.text_input(f"Subject Code {i+1}", help="Official ID (Optional)", key=f"scode_{i}")
        
        # Faculty for this subject
        fac_input = st.text_input(f"Faculty Members for {s_name if s_name else 'Subject '+str(i+1)}", 
                                  placeholder="Separate names with commas (e.g. Dr. Smith, Prof. Doe)", key=f"fac_{i}")
        
        if s_name:
            # Process faculty string into list
            fac_list = [f.strip() for f in fac_input.split(',')] if fac_input else []
            
            subjects_data.append({
                "name": s_name,
                "acronym": s_acro if s_acro else s_name[:3].upper(),
                "code": s_code
            })
            faculty_map[s_name] = fac_list

# --- GENERATION ---
if st.button("Generate Timetable", type="primary"):
    # Validation
    valid = True
    for sub in subjects_data:
        if not faculty_map.get(sub['name']):
            st.error(f"Subject '{sub['name']}' has no faculty assigned!")
            valid = False
            
    if valid:
        ga = GeneticAlgorithm(subjects_data, faculty_map, breaks, num_classes, num_sections, start_time, end_time)
        with st.spinner("Evolution in progress... (Optimizing schedule)"):
            best_schedule = ga.optimize()
            st.session_state.timetable_data = best_schedule
            st.session_state.generated = True
            st.success("Timetable Generated Successfully!")

# --- POST-GENERATION SETTINGS & EXPORT ---
if st.session_state.get('generated'):
    st.divider()
    st.header("4. Finalize & Export")
    
    # Per-Section Details (Opt-in)
    st.subheader("Section Details (Optional)")
    section_details = {}
    
    cols = st.columns(min(num_sections, 3)) # Max 3 columns for layout
    
    for i in range(1, num_sections + 1):
        sec_name = f"Section {i}"
        with cols[(i-1) % 3]:
            st.markdown(f"**{sec_name}**")
            room = st.text_input(f"Room No ({sec_name})", key=f"room_{i}")
            in_charge = st.text_input(f"Class In-Charge ({sec_name})", key=f"ic_{i}")
            section_details[sec_name] = {'room': room, 'in_charge': in_charge}

    if st.button("Download PDF Report"):
        # Prepare Config Dictionary
        pdf_config = {
            'org_name': org_name,
            'subtitle': subtitle,
            'dept_name': dept_name,
            'academic_label': academic_label,
            'logo_bytes': uploaded_logo
        }
        
        # Extract Time Slots for Header
        # We grab the slots from the first day of the first section to keep it consistent
        first_sec = list(st.session_state.timetable_data.keys())[0]
        # logic: timetable_data[sec]['Monday'] -> returns list of (time_tuple, subj, fac)
        # we need just the time_tuples
        raw_slots = [x[0] for x in st.session_state.timetable_data[first_sec]["Monday"]]
        
        pdf_file = export_to_pdf(st.session_state.timetable_data, raw_slots, pdf_config, section_details)
        
        st.download_button(
            label="Download PDF",
            data=pdf_file,
            file_name=f"{branch_name}_Timetable.pdf",
            mime="application/pdf"
        )
        
    # Preview (Simple Table)
    st.subheader("Preview (Section 1)")
    first_sec = list(st.session_state.timetable_data.keys())[0]
    sec_data = st.session_state.timetable_data[first_sec]
    
    # Flatten for display
    preview_data = []
    for day, items in sec_data.items():
        row = {"Day": day}
        for idx, (time_slot, sub_data, fac) in enumerate(items):
            if sub_data == "BREAK":
                val = "BREAK"
            else:
                val = f"{sub_data['acronym']} ({fac})"
            row[f"Slot {idx+1}"] = val
        preview_data.append(row)
        
    st.dataframe(pd.DataFrame(preview_data))

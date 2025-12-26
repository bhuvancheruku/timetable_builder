import random
import copy
import io
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

class GeneticAlgorithm:
    def __init__(self, subjects, faculty_members, breaks, num_classes, num_sections, start_time, end_time):
        self.subjects = subjects 
        self.faculty_members = faculty_members
        self.breaks = breaks
        self.num_classes = num_classes
        self.num_sections = num_sections
        self.start_time = start_time
        self.end_time = end_time
        
        self.population_size = 50
        self.generations = 100
        self.mutation_rate = 0.1
        self.elite_size = 2

    def create_time_slots(self):
        """Calculates valid class slots excluding breaks."""
        time_slots = []
        current_time = self.start_time
        
        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)
        total_minutes = (end_dt - start_dt).seconds // 60
        
        total_break_minutes = sum(duration for _, duration in self.breaks)
        available_minutes = total_minutes - total_break_minutes
        
        if self.num_classes > 0:
            class_duration = available_minutes // self.num_classes
        else:
            class_duration = 60

        for _ in range(self.num_classes):
            # Check for breaks at the current time
            for break_time, break_duration in self.breaks:
                if current_time == break_time:
                    break_end = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=break_duration)).time()
                    time_slots.append((current_time, "BREAK"))
                    current_time = break_end
            
            # Add Class Slot
            class_end_dt = datetime.combine(datetime.today(), current_time) + timedelta(minutes=class_duration)
            class_end_time = class_end_dt.time()
            
            if class_end_time <= self.end_time:
                time_slots.append((current_time, class_end_time))
                current_time = class_end_time
                
        return time_slots

    def generate_random_schedule(self):
        schedule = {}
        available_time_slots = self.create_time_slots()
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        
        for section in range(1, self.num_sections + 1):
            section_schedule = {}
            for day in days:
                daily_schedule = []
                for time_slot in available_time_slots:
                    if time_slot[1] == "BREAK":
                        daily_schedule.append((time_slot, "BREAK", ""))
                        continue
                    
                    subject_obj = random.choice(self.subjects)
                    fac_list = self.faculty_members.get(subject_obj['name'], [])
                    faculty = random.choice(fac_list) if fac_list else "TBA"
                    
                    daily_schedule.append((time_slot, subject_obj, faculty))
                section_schedule[day] = daily_schedule
            schedule[f"Section {section}"] = section_schedule
        return schedule

    def fitness(self, schedule):
        score = 1000
        conflicts = 0
        faculty_time_tracker = {} 

        for section, days in schedule.items():
            for day, classes in days.items():
                daily_subjects = []
                for time_slot_tuple in classes:
                    time_slot = time_slot_tuple[0]
                    subject_data = time_slot_tuple[1]
                    faculty = time_slot_tuple[2]

                    if subject_data == "BREAK":
                        continue
                    
                    subject_name = subject_data['name']
                    if subject_name in daily_subjects:
                        score -= 5 
                    daily_subjects.append(subject_name)

                    time_key = (day, time_slot)
                    if time_key not in faculty_time_tracker:
                        faculty_time_tracker[time_key] = []
                    
                    if faculty in faculty_time_tracker[time_key]:
                        conflicts += 1
                        score -= 50
                    else:
                        faculty_time_tracker[time_key].append(faculty)
        return score

    def crossover(self, parent1, parent2):
        child = copy.deepcopy(parent1)
        sections = list(parent1.keys())
        for section in sections:
            if random.random() > 0.5:
                child[section] = copy.deepcopy(parent2[section])
        return child

    def mutate(self, schedule):
        if random.random() < self.mutation_rate:
            section = random.choice(list(schedule.keys()))
            day = random.choice(list(schedule[section].keys()))
            if not schedule[section][day]: return schedule
            
            class_idx = random.randint(0, len(schedule[section][day]) - 1)
            current_slot = schedule[section][day][class_idx]
            
            if current_slot[1] != "BREAK":
                new_subject = random.choice(self.subjects)
                fac_list = self.faculty_members.get(new_subject['name'], [])
                new_faculty = random.choice(fac_list) if fac_list else "TBA"
                schedule[section][day][class_idx] = (current_slot[0], new_subject, new_faculty)
        return schedule

    def optimize(self):
        population = [self.generate_random_schedule() for _ in range(self.population_size)]
        
        for generation in range(self.generations):
            population = sorted(population, key=self.fitness, reverse=True)
            new_population = population[:self.elite_size]
            
            while len(new_population) < self.population_size:
                tournament = random.sample(population, 5)
                parent1 = max(tournament, key=self.fitness)
                tournament = random.sample(population, 5)
                parent2 = max(tournament, key=self.fitness)
                
                child = self.crossover(parent1, parent2)
                child = self.mutate(child)
                new_population.append(child)
            population = new_population

        return max(population, key=self.fitness)


# --- UNIVERSAL PDF EXPORT FUNCTION ---
def format_time_12hr(t):
    """Converts datetime.time or string to 12-hour format string (e.g., 01:30 PM)."""
    if isinstance(t, str):
        return t
    return t.strftime("%I:%M %p")

def export_to_pdf(timetables, time_slots, config, section_details):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=16, spaceAfter=5)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, spaceAfter=2)
    header_info_style = ParagraphStyle('HeaderInfo', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11, spaceAfter=15, fontName='Helvetica-Bold')
    
    def get_header_elements(section_name):
        header_elems = []
        if config.get('logo_bytes'):
            try:
                img = Image(config['logo_bytes'], width=1.0*inch, height=1.0*inch)
                img.hAlign = 'CENTER'
                header_elems.append(img)
            except:
                pass
        
        if config.get('org_name'):
            header_elems.append(Paragraph(config['org_name'], title_style))
        if config.get('subtitle'):
            header_elems.append(Paragraph(config['subtitle'], subtitle_style))
        
        header_elems.append(Spacer(1, 10))
        
        dept_text = config.get('dept_name', '')
        acad_text = config.get('academic_label', '')
        room = section_details.get(section_name, {}).get('room', '')
        room_text = f" | Room No: {room}" if room else ""
        
        full_info = f"{dept_text}<br/>{acad_text}<br/>Section: {section_name}{room_text}"
        header_elems.append(Paragraph(full_info, header_info_style))
        return header_elems

    for section_idx, (section, timetable) in enumerate(timetables.items()):
        if section_idx > 0:
            elements.append(PageBreak())

        elements.extend(get_header_elements(section))
        
        # Build Table Headers
        table_headers = ["Day/Time"]
        for start, end in time_slots:
            if end == "BREAK":
                table_headers.append("BREAK")
            else:
                # Format: 09:00 AM <newline> 10:10 AM
                table_headers.append(f"{format_time_12hr(start)}\n{format_time_12hr(end)}")
        
        data = [table_headers]
        section_subjects_map = {}

        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
            row = [day]
            if day in timetable:
                for time_slot, subject_data, faculty in timetable[day]:
                    if subject_data == "BREAK":
                        row.append("BREAK")
                    else:
                        acronym = subject_data.get('acronym', subject_data['name'][:3].upper())
                        cell_text = f"<b>{acronym}</b>\n({faculty})"
                        row.append(Paragraph(cell_text, styles['BodyText']))
                        
                        s_code = subject_data.get('code', 'N/A')
                        s_name = subject_data.get('name', '')
                        if s_name not in section_subjects_map:
                            section_subjects_map[s_name] = {'code': s_code, 'name': s_name, 'faculty': faculty}
            else:
                row.extend([""] * len(time_slots))
            data.append(row)

        col_widths = [0.8*inch] + [1.1*inch] * (len(table_headers)-1)
        tt_table = Table(data, colWidths=col_widths)
        tt_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elements.append(tt_table)
        elements.append(Spacer(1, 20))

        # Footer Details
        footer_data = [["Subject Code", "Subject Name", "Faculty Name"]]
        for s_info in section_subjects_map.values():
            footer_data.append([
                s_info['code'] if s_info['code'] else "-",
                Paragraph(s_info['name'], styles['BodyText']),
                s_info['faculty']
            ])
        
        if len(footer_data) > 1:
            elements.append(Paragraph("<b>Details of Faculty/Instructor:</b>", styles['Normal']))
            elements.append(Spacer(1, 5))
            f_table = Table(footer_data, colWidths=[1.5*inch, 4*inch, 2.5*inch], hAlign='LEFT')
            f_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(f_table)
            elements.append(Spacer(1, 25))

        # Signatures
        in_charge = section_details.get(section, {}).get('in_charge', '')
        sig_data = [[f"Class In-Charge: {in_charge}", "Head of Department"]]
        sig_table = Table(sig_data, colWidths=[4*inch, 4*inch])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer

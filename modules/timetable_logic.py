import random
import pandas as pd
from datetime import datetime, timedelta
import io
import copy
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

class GeneticAlgorithm:
    def __init__(self, subjects, faculty_members, breaks, num_classes, num_sections, start_time, end_time):
        self.subjects = subjects
        self.faculty_members = faculty_members
        self.breaks = breaks
        self.num_classes = num_classes
        self.num_sections = num_sections
        self.start_time = start_time
        self.end_time = end_time
        # GA Hyperparameters
        self.population_size = 50
        self.generations = 100
        self.mutation_rate = 0.1
        self.elite_size = 2

    def create_time_slots(self):
        """Calculates valid class slots excluding breaks."""
        time_slots = []
        current_time = self.start_time
        
        # Calculate total available minutes
        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)
        total_minutes = (end_dt - start_dt).seconds // 60
        
        # Subtract break duration
        total_break_minutes = sum(duration for _, duration in self.breaks)
        available_minutes = total_minutes - total_break_minutes
        
        # Determine class duration (floored to avoid overshooting)
        if self.num_classes > 0:
            class_duration = available_minutes // self.num_classes
        else:
            class_duration = 60 # Default safe fallback

        for _ in range(self.num_classes):
            # Check if current time is a break time
            for break_time, break_duration in self.breaks:
                if current_time == break_time:
                    break_end = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=break_duration)).time()
                    time_slots.append((current_time, "BREAK"))
                    current_time = break_end
            
            # Calculate class end time
            class_end_dt = datetime.combine(datetime.today(), current_time) + timedelta(minutes=class_duration)
            class_end_time = class_end_dt.time()
            
            if class_end_time <= self.end_time:
                time_slots.append((current_time, class_end_time))
                current_time = class_end_time
                
        return time_slots

    def generate_random_schedule(self):
        """Creates a single random schedule."""
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
                    
                    # Randomly assign a subject and a faculty member
                    subject = random.choice(self.subjects)
                    faculty = random.choice(self.faculty_members[subject])
                    daily_schedule.append((time_slot, subject, faculty))
                section_schedule[day] = daily_schedule
            schedule[f"Section {section}"] = section_schedule
        return schedule

    def fitness(self, schedule):
        """Calculates how 'good' a schedule is. Higher is better."""
        score = 1000  # Start with a high base score
        conflicts = 0
        
        # Tracking to find faculty clashes across different sections
        faculty_time_tracker = {} # Key: (Day, TimeSlot), Value: [FacultyNames]

        for section, days in schedule.items():
            for day, classes in days.items():
                daily_subjects = []
                for time_slot_tuple in classes:
                    # Unpack the tuple properly
                    time_slot = time_slot_tuple[0] # (start, end)
                    subject = time_slot_tuple[1]
                    faculty = time_slot_tuple[2]

                    if subject == "BREAK":
                        continue
                    
                    # Constraint 1: Subject Repetition per day (Soft Constraint)
                    # We prefer diverse subjects in a day, but it's not fatal.
                    if subject in daily_subjects:
                        score -= 5 
                    daily_subjects.append(subject)

                    # Constraint 2: Faculty Clash (Hard Constraint)
                    # A faculty cannot be in two sections at the same time
                    time_key = (day, time_slot)
                    if time_key not in faculty_time_tracker:
                        faculty_time_tracker[time_key] = []
                    
                    if faculty in faculty_time_tracker[time_key]:
                        conflicts += 1
                        score -= 50 # Heavy penalty for physical impossibility
                    else:
                        faculty_time_tracker[time_key].append(faculty)

        return score

    def crossover(self, parent1, parent2):
        """Mixes two schedules to create a child."""
        child = copy.deepcopy(parent1)
        sections = list(parent1.keys())
        
        # Swap entire section schedules between parents
        for section in sections:
            if random.random() > 0.5:
                child[section] = copy.deepcopy(parent2[section])
        return child

    def mutate(self, schedule):
        """Randomly changes a class to maintain diversity."""
        if random.random() < self.mutation_rate:
            section = random.choice(list(schedule.keys()))
            day = random.choice(list(schedule[section].keys()))
            class_idx = random.randint(0, len(schedule[section][day]) - 1)
            
            current_slot = schedule[section][day][class_idx]
            
            # Don't mutate breaks
            if current_slot[1] != "BREAK":
                new_subject = random.choice(self.subjects)
                new_faculty = random.choice(self.faculty_members[new_subject])
                # Keep the time slot, update subject/faculty
                schedule[section][day][class_idx] = (current_slot[0], new_subject, new_faculty)
        return schedule

    def optimize(self):
        """Runs the genetic algorithm."""
        population = [self.generate_random_schedule() for _ in range(self.population_size)]
        
        for generation in range(self.generations):
            # Sort population by fitness (descending)
            population = sorted(population, key=self.fitness, reverse=True)
            
            # Elitism: Keep the best schedules
            new_population = population[:self.elite_size]
            
            # Generate rest of the population
            while len(new_population) < self.population_size:
                # Tournament Selection (Pick random 5, choose best)
                tournament = random.sample(population, 5)
                parent1 = max(tournament, key=self.fitness)
                tournament = random.sample(population, 5)
                parent2 = max(tournament, key=self.fitness)
                
                child = self.crossover(parent1, parent2)
                child = self.mutate(child)
                new_population.append(child)
            
            population = new_population

        # Return the best schedule found
        return max(population, key=self.fitness)


def export_to_pdf(timetables, time_slots, branch_name):
    """Exports the generated schedule to a PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Title
    styles = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
    ])

    for section, timetable in timetables.items():
        # Header Row
        header = ["Day"] + [f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}" if end != "BREAK" else "BREAK" for start, end in time_slots]
        data = [header]
        
        for day, classes in timetable.items():
            row = [day]
            for time_slot, subject, faculty in classes:
                if subject == "BREAK":
                    row.append("BREAK")
                else:
                    row.append(f"{subject}\n({faculty})")
            data.append(row)
        
        # Create Table
        # Adjust column widths dynamically or set fixed
        col_count = len(header)
        table = Table(data, colWidths=[50] + [55] * (col_count - 1))
        table.setStyle(styles)
        
        elements.append(Table([[f"Timetable for {branch_name} - {section}"]], style=[('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        elements.append(table)
        elements.append(Table([[""]], colWidths=[1])) # Spacer
        
    doc.build(elements)
    buffer.seek(0)
    return buffer

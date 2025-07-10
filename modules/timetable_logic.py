import random
import pandas as pd
from datetime import datetime, timedelta
import io
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
        self.population_size = 50
        self.generations = 100

    def generate_random_schedule(self):
        schedule = {}
        available_time_slots = self.create_time_slots()
        for section in range(1, self.num_sections + 1):
            section_schedule = {}
            for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]:
                daily_schedule = []
                assigned_subjects = set()
                for time_slot in available_time_slots:
                    if time_slot[1] == "BREAK":
                        daily_schedule.append((time_slot, "BREAK", ""))
                        continue
                    subject = random.choice([sub for sub in self.subjects if sub not in assigned_subjects])
                    assigned_subjects.add(subject)
                    faculty = random.choice(self.faculty_members[subject])
                    daily_schedule.append((time_slot, subject, faculty))
                section_schedule[day] = daily_schedule
            schedule[f"Section {section}"] = section_schedule
        return schedule

    def create_time_slots(self):
        time_slots = []
        current_time = self.start_time
        class_duration = (datetime.combine(datetime.today(), self.end_time) - datetime.combine(datetime.today(), self.start_time)).seconds // 60
        class_duration = (class_duration - sum(duration for _, duration in self.breaks)) // self.num_classes
        for _ in range(self.num_classes):
            for break_time, break_duration in self.breaks:
                if current_time == break_time:
                    break_end = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=break_duration)).time()
                    time_slots.append((current_time, "BREAK"))
                    current_time = break_end
            class_end_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=class_duration)).time()
            if class_end_time <= self.end_time:
                time_slots.append((current_time, class_end_time))
                current_time = class_end_time
        return time_slots

    def fitness(self, schedule):
        score = 100
        for section, days in schedule.items():
            for day, classes in days.items():
                assigned_subjects = set()
                assigned_faculty = {}
                for time_slot, subject, faculty in classes:
                    if subject == "BREAK":
                        continue
                    if subject in assigned_subjects:
                        score -= 10
                    else:
                        assigned_subjects.add(subject)
                    if faculty in assigned_faculty:
                        if assigned_faculty[faculty] == time_slot:
                            score -= 10
                    else:
                        assigned_faculty[faculty] = time_slot
        return score

    def initial_population(self):
        return [self.generate_random_schedule() for _ in range(self.population_size)]

    def crossover(self, parent1, parent2):
        return parent1

    def mutate(self, schedule):
        return schedule

    def optimize(self):
        population = self.initial_population()
        best_schedule = None
        best_fitness = -float('inf')
        for _ in range(self.generations):
            for schedule in population:
                fitness_score = self.fitness(schedule)
                if fitness_score > best_fitness:
                    best_fitness = fitness_score
                    best_schedule = schedule
        return best_schedule


def export_to_pdf(timetables, time_slots, branch_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    for section, timetable in timetables.items():
        data = [["Day"] + [f"{start} - {end}" if end != "BREAK" else "BREAK" for start, end in time_slots]]
        for day, classes in timetable.items():
            row = [day]
            for time_slot, subject, faculty in classes:
                row.append("BREAK" if subject == "BREAK" else f"{subject}\n{faculty}")
            data.append(row)
        timetable_table = Table(data, colWidths=[50] + [65] * len(time_slots))
        timetable_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(timetable_table)
        elements.append(Table([[""]], colWidths=[1]))
    doc.build(elements)
    buffer.seek(0)
    return buffer

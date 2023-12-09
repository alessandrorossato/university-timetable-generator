import pyomo.environ as pyo
from itertools import product
import pandas as pd
import json
import school_classes as cl
import school_model as mod


# sets
period = ["1° Periodo", "2° Periodo", "3° Periodo", "4° Periodo"]
campus = ["San Giobbe", "Palazzo Moro"]
qualifications = json.load(open("data/input/qualifications_levels.json"))
profiles = json.load(open("data/input/profiles.json"))
calendar = (4,6,6)

# load data
school = cl.School.create_school_from_data("data/input/UniveCourses.csv", qualifications, profiles, "data/input/aule_.csv", calendar)
# courses = school.course_classes
# teachers = school.teacher_classes
# teachings = school.teaching_classes
# rooms = school.room_classes
# calendar = school.calendar_classes

# define par: period, max_room_size, max_h_daily, free_rooms_hourly, max_elective_overlap
parameters = cl.define_parameters(period[2], "relaxed")

# filter data
school.calendar_classes = cl.CalendarClass.filter_by(school.calendar_classes, "period", [2])
school.room_classes = cl.BaseClass.filter_by(school.room_classes, "campus", campus)
school.course_classes = cl.BaseClass.filter_by(school.course_classes, "campus", campus)
school.teaching_classes = cl.BaseClass.filter_by(school.teaching_classes, "campus", campus)
school.teaching_classes = cl.BaseClass.filter_by(school.teaching_classes, "period", ["3° Periodo"])

# remove teachings from courses and teachers outside the periods and campus # da inserire in filter_by
for course in school.course_classes:
    course.teachings = [
        teaching
        for teaching in course.teachings
        if teaching.period == "3° Periodo" and teaching.campus in campus
    ]
    
for teacher in school.teacher_classes:
    teacher.teachings = [
        teaching
        for teaching in teacher.teachings
        if teaching.period == "3° Periodo" and teaching.campus in campus
    ]

#  remove courses and teachers without teachings, and teachings without courses and teachers
school.course_classes = [
    course
    for course in school.course_classes
    if len(course.teachings) > 0
]

school.teacher_classes = [
    teacher
    for teacher in school.teacher_classes
    if len(teacher.teachings) > 0
]


# ----------------------------------Model & Sets------------------------------------
sets = mod.set_creation(school)
model = mod.model_creation()

# ------------------------------------Variables-------------------------------------
model.x, model.y, model.z = mod.model_variables(model, sets)

# ------------------------------------Parameters------------------------------------
model.prof_cost, model.cal_cost = mod.model_parameters(model, sets, school, profiles)

# --------------------------------Objective function--------------------------------
model.obj = mod.model_objective(model, sets, school)

# ----------------------------------Costraint---------------------------------------
# Assignment Costraint
model.all_courses = mod.all_courses(model, sets, school)
model.all_teachers = mod.all_teachers(model, sets, school)
model.all_rooms = mod.all_rooms(model, sets, school)
model.room_size = mod.room_size(model, sets, school, parameters)

# Ubiquity Costraint
model.ubiquity_stud = mod.ubiquity_stud(model, sets, school, parameters)
model.ubiquity_professor = mod.ubiquity_professor(model, sets, school)
model.ubiquity_rooms = mod.ubiquity_rooms(model, sets, school)

# Liniking Variables
model.link_z_x = mod.link_z_x(model, sets, school)
model.link_y_x = mod.link_y_x(model, sets, school)

# Daily Costraint
model.repeat_teaching = mod.repeat_teaching(model, sets, school)
model.student_presence = mod.student_presence(model, sets, school)
model.professor_presence = mod.professor_presence(model, sets, school)

# Optional Constraints
model.free_room = mod.free_room(model, sets, school, parameters)
# model.max_hours_per_day = mod.max_hours_per_day(model, sets, school, parameters)
model.professor_limit = mod.professor_limit(model, sets, school)


# --------------------------------Solver--------------------------------
solver = pyo.SolverFactory(
    "cplex",
    executable="C:/Program Files/IBM/ILOG/CPLEX_Studio2211/cplex/bin/x64_win64/cplex.exe",
)
solver.options['timelimit'] = 600
results = solver.solve(model, tee=True)
print(results)
print(model.obj())


# --------------------------------Output--------------------------------
days = [d for d, h in list(product(sets["days"], sets["hours"]))]
hours = [h for d, h in list(product(sets["days"], sets["hours"]))]
# --------------------------------ROOM OCCUPATION--------------------------------

cal_r = pd.DataFrame(columns=list(school.room_classes))
cal_r["day"] = days
cal_r["hour"] = hours
cal_r.set_index([days, hours], inplace=True)
cal_r.drop(["day", "hour"], axis=1, inplace=True)

for d in days:
    for h in hours:
        for t in school.teaching_classes:
            for r in school.room_classes:
                if pyo.value(model.z[d, h, t.name, r.name]) == 1:
                    cal_r.loc[(d, h), r.name] = t.name

cal_r.fillna("-", inplace=True)
# pd.set_option("display.max_columns", None)
# pd.set_option("display.max_colwidth", 1000)
# print(cal_r)
cal_r.to_csv("data/output/schedule_rooms.csv")

# --------------------------------PROFESSOR SCHEDULE--------------------------------
# Creating the output dataset
cal_p = pd.DataFrame(columns=list(school.teacher_classes))
cal_p["day"] = days
cal_p["hour"] = hours
cal_p.set_index([days, hours], inplace=True)
cal_p.drop(["day", "hour"], axis=1, inplace=True)

for d in days:
    for h in hours:
        for teacher in school.teacher_classes:
            for teaching in teacher.teachings:
                if pyo.value(model.y[d, h, teacher.name, teaching.name]) == 1:
                    cal_p.loc[(d, h), teacher.name] = teaching.name

cal_p.fillna("-", inplace=True)
# pd.set_option("display.max_columns", None)
# pd.set_option("display.max_colwidth", 1000)
# print(cal_p)
cal_p.to_csv("data/output/schedule_teachers.csv")

# --------------------------------COURSE SCHEDULE--------------------------------
cal_c = pd.DataFrame(columns=list(school.course_classes))
cal_c["day"] = days
cal_c["hour"] = hours
cal_c.set_index([days, hours], inplace=True)
cal_c.drop(["day", "hour"], axis=1, inplace=True)

# # Printing the rooms where lectures take place
# for d in days:
#     for h in hours:
#         for course in courses:
#             for teaching in course.teachings:
#                 if pyo.value(model.x[d, h, course.name, teaching.name]) == 1:
#                     cal_c.loc[(d, h), course.name] = teaching.name
                    
for d in days:
    for h in hours:
        for course in school.course_classes:
            teachings_for_cell = []  # Lista per memorizzare tutti gli insegnamenti per la stessa cella
            for teaching in course.teachings:
                if pyo.value(model.x[d, h, course.name, teaching.name]) == 1:
                    # Aggiungi gli insegnamenti alla lista
                    # teaching_identifier = f"{teaching.name}_{i}"
                    teachings_for_cell.append(teaching.name)
            
            # Unisci gli insegnamenti separati da virgola nella stessa cella
            cal_c.loc[(d, h), course.name] = ", ".join(teachings_for_cell)

cal_c.fillna("-", inplace=True)
# pd.set_option("display.max_columns", None)
# pd.set_option("display.max_colwidth", 1000)
# print(cal_c)
cal_c.to_csv("data/output/schedule_courses.csv")

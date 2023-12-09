import pyomo.environ as pyo
import pyomo.kernel as pmo
import random


# ------------------------------------Sets------------------------------------
def set_creation(school):
    days_ = set([i.day for i in school.calendar_classes])
    hours_ = set([i.hour for i in school.calendar_classes])
    rooms_ = set(i.name for i in school.room_classes)
    teachings_ = set(i.name for i in school.teaching_classes)
    courses_ = set([i.name for i in school.course_classes])
    teachers_ = set(i.name for i in school.teacher_classes)
    return dict(
        days=days_,
        hours=hours_,
        rooms=rooms_,
        teachings=teachings_,
        courses=courses_,
        teachers=teachers_,
    )


def unpack_sets(sets):
    days_ = sets["days"]
    hours_ = sets["hours"]
    rooms_ = sets["rooms"]
    teachings_ = sets["teachings"]
    courses_ = sets["courses"]
    teachers_ = sets["teachers"]
    return days_, hours_, rooms_, teachings_, courses_, teachers_


# ------------------------------------Model------------------------------------
def model_creation():
    model = pyo.ConcreteModel(name="Classroom Timetable")
    print(f"Model name: ", model.name)
    return model


# ------------------------------------Variables------------------------------------
def model_variables(model, sets):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.x = pyo.Var(days_, hours_, courses_, teachings_, domain=pmo.Binary)
    model.y = pyo.Var(days_, hours_, teachers_, teachings_, domain=pmo.Binary)
    model.z = pyo.Var(days_, hours_, teachings_, rooms_, domain=pmo.Binary)
    print(f"Variables defined: ", model.x, model.y, model.z)
    return model.x, model.y, model.z


# ------------------------------------Parameters------------------------------------
def prof_cost(model, sets, school, profiles):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.prof_cost = pyo.Param(days_, hours_, teachers_, initialize=1, mutable=True)
    for day in days_:
        for hour in hours_:
            for teacher in school.teacher_classes:
                if (
                    day in profiles[teacher.profile]["days"]
                    and hour in profiles[teacher.profile]["hours"]
                ):
                    model.prof_cost[day, hour, teacher.name] = (
                        50 + random.randint(-5, 5)
                    ) * teacher.seniority
                else:
                    model.prof_cost[day, hour, teacher.name] = 1
    return model.prof_cost


def cal_cost(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.cal_cost = pyo.Param(days_, hours_, teachings_, initialize=0, mutable=True)
    for day in days_:
        for hour in hours_:
            for teaching in teachings_:
                model.cal_cost[day, hour, teaching] = [
                    c.cost
                    for c in school.calendar_classes
                    if c.day == day and c.hour == hour
                ][0]
    return model.cal_cost


# def overlap_cost(model, sets, school):
#     days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
#     teaching2 = teachings_
#     model.overlap_cost = pyo.Param(days_, hours_, teachings_, teaching2, initialize=0, mutable=True)
#     for day in days_:
#         for hour in hours_:
#             for course in school.course_classes:
#                 for teaching, other_teaching in combinations_with_replacement(course.teachings, 2):
#                     if teaching == other_teaching:
#                         model.overlap_cost[day, hour, teaching.name, other_teaching.name] = 0
#                     else:
#                         model.overlap_cost[day, hour, teaching.name, other_teaching.name] = 500

#     return model.overlap_cost


def model_parameters(model, sets, school, profiles):
    model.prof_cost = prof_cost(model, sets, school, profiles)
    model.cal_cost = cal_cost(model, sets, school)
    # model.overlap_cost = overlap_cost(model, sets, school)
    print("Parameters defined: prof_cost, cal_cost")
    return model.prof_cost, model.cal_cost  # , model.overlap_cost


# --------------------------------Objective function--------------------------------
def model_objective(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)

    model.obj = pyo.Objective(
        sense=pyo.minimize,
        expr=sum(
            model.prof_cost[day, hour, teacher.name]
            * model.y[day, hour, teacher.name, teach.name]
            for day in days_
            for hour in hours_
            for teacher in school.teacher_classes
            for teach in teacher.teachings
        )
        + sum(
            model.cal_cost[day, hour, teaching.name]
            * model.x[day, hour, course.name, teaching.name]
            for day in days_
            for hour in hours_
            for course in school.course_classes
            for teaching in course.teachings
        )
        # + sum(
        #     model.overlap_cost[day, hour, teaching.name, other_teaching.name]
        #     * model.x[day, hour, course.name, teaching.name]
        #     # * model.x[day, hour, course.name, other_teaching.name]
        #     for day in days_
        #     for hour in hours_
        #     for course in courses_
        #     for teaching in course.teachings
        #     for other_teaching in course.teachings
        #     if teaching != other_teaching
        # )
    )
    print("Objective function defined: ", model.obj)
    return model.obj


# --------------------------------Assignment Costraint--------------------------------


# 1. All lectures must be assigned, both for mandatory courses and elective
def all_courses(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.all_courses = pyo.ConstraintList()
    for course in school.course_classes:
        for teaching in course.teachings:
            model.all_courses.add(
                sum(
                    model.x[d, h, course.name, teaching.name]
                    for d in days_
                    for h in hours_
                )
                == teaching.frequency
            )
    print("1. All Course lectures must be assigned")
    return model.all_courses


# 2. The sum of the lectures in a particular teaching of a professor, must be equal to the total hours to be assigned
def all_teachers(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.all_teachers = pyo.ConstraintList()
    for teacher in school.teacher_classes:
        for teaching in teacher.teachings:
            model.all_teachers.add(
                sum(
                    model.y[d, h, teacher.name, teaching.name]
                    for d in days_
                    for h in hours_
                )
                == teaching.frequency
            )
    print("2. All Teacher lectures must be assigned")
    return model.all_teachers


# 3. During the whole week, the number of times rooms are occupied by a teaching must be equal to the total number of lectures that must be assigned for that teaching
def all_rooms(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.all_rooms = pyo.ConstraintList()
    for course in school.course_classes:
        for teaching in course.teachings:
            model.all_rooms.add(
                sum(
                    model.z[d, h, teaching.name, room.name]
                    for d in days_
                    for h in hours_
                    for room in school.room_classes
                )
                == teaching.frequency
            )
    print("3. All Room lecture must be assigned")
    return model.all_rooms


# 4. Fit the size of rooms for each course
def room_size(model, sets, school, parameters):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.room_size = pyo.ConstraintList()
    for d in days_:
        for h in hours_:
            for room in school.room_classes:
                for course in school.course_classes:
                    for teaching in course.teachings:
                        if teaching.size > room.size:
                            model.room_size.add(
                                model.z[d, h, teaching.name, room.name] == 0
                            )
                        elif room.size > teaching.size + parameters[1]:  # max_room_size
                            model.room_size.add(
                                model.z[d, h, teaching.name, room.name] == 0
                            )
                        else:
                            model.room_size.add(
                                model.z[d, h, teaching.name, room.name]
                                <= model.x[d, h, course.name, teaching.name]
                            )
    print("4. Room size must fit the teaching size")
    return model.room_size


# --------------------------------Ubiquity Costraint--------------------------------

# 5. Students can follow only one teaching in a time slot except for different partition
def ubiquity_stud(model, sets, school, parameters):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.ubiquity_stud = pyo.ConstraintList()
    for day in days_:
        for hour in hours_:
            for course in school.course_classes:
                if course.partition == "NO":
                    for teaching in course.teachings:
                        if teaching.elective == "Obbligatorio":
                            model.ubiquity_stud.add(
                                sum(
                                    model.x[day, hour, course.name, teaching.name]
                                    for teaching in course.teachings
                                    if teaching.elective == "Obbligatorio"
                                )
                                <= 1
                            )
                        else:
                            model.ubiquity_stud.add(
                                sum(
                                    model.x[day, hour, course.name, teaching.name]
                                    for teaching in course.teachings
                                    if teaching.elective != "Obbligatorio"
                                )
                                <= parameters[4]
                            )
                else:
                    for partition in course.partition:
                        for teaching in course.teachings:
                            if teaching.partition == partition:
                                if teaching.elective == "Obbligatorio":
                                    model.ubiquity_stud.add(
                                        sum(
                                            model.x[day, hour, course.name, teaching.name]
                                            for teaching in course.teachings
                                            if teaching.elective == "Obbligatorio"
                                        )
                                        <= 1
                                    )
                                else:
                                    model.ubiquity_stud.add(
                                        sum(
                                            model.x[day, hour, course.name, teaching.name]
                                            for teaching in course.teachings
                                            if teaching.elective != "Obbligatorio"
                                        )
                                        <= parameters[4]
                                        * (1 - sum(
                                                model.x[day, hour, course.name, teaching.name]
                                                for teaching in course.teachings
                                                if teaching.elective == "Obbligatorio"
                                            )
                                        )
                                    )
    print("5. Students can follow only one teaching in a time slot except for different partition")
    return model.ubiquity_stud


# 6. The professor can teach only one lecture at a given time
def ubiquity_professor(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.ubiquity_professor = pyo.ConstraintList()
    for d in days_:
        for h in hours_:
            for teacher in school.teacher_classes:
                model.ubiquity_professor.add(
                    sum(
                        model.y[d, h, teacher.name, teaching.name]
                        for teaching in teacher.teachings
                    )
                    <= 1
                )
    print("6. Professor can teach only one lecture at a given time")
    return model.ubiquity_professor

# 7. There cannot be more than 1 lecture in a room in a given moment
def ubiquity_rooms(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.ubiquity_rooms = pyo.ConstraintList()
    for d in days_:
        for h in hours_:
            for room in school.room_classes:
                model.ubiquity_rooms.add(
                    sum(model.z[d, h, teaching.name, room.name] for teaching in school.teaching_classes)
                    <= 1
                )
    print("7. There cannot be more than one lecture in a room in a given moment")
    return model.ubiquity_rooms

# --------------------------------Liniking Variables--------------------------------

# 8. Linking z and x: in a given moment, if a teaching of a course has a lecture, then it is in one room
def link_z_x(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.link_z_x = pyo.ConstraintList()
    for d in days_:
        for h in hours_:
            for course in school.course_classes:
                for teaching in course.teachings:
                    model.link_z_x.add(
                        sum(model.z[d, h, teaching.name, room.name] for room in school.room_classes)
                        == model.x[d, h, course.name, teaching.name]
                    )
    print("8. Linking z and x: in a given moment, if course has a lecture, then it is in the same room of the same teaching")
    return model.link_z_x

# 9. Linking the binary variable y with x, in a given moment, if there's a lecture of a teaching, then one of the professors that teach that teaching will have lecture
def link_y_x(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.link_y_x = pyo.ConstraintList()
    for d in days_:
        for h in hours_:
            for course in school.course_classes:
                for teaching in course.teachings:
                    model.link_y_x.add(
                        sum(
                            model.y[d, h, teacher.name, teaching.name]
                            for teacher in school.teacher_classes
                            if teaching in teacher.teachings
                        )
                        == model.x[d, h, course.name, teaching.name]
                    )
    print("9. Linking y and x: in a given moment, if there's a lecture of a teaching, then the professors that teach that teaching will have lecture")
    return model.link_y_x

# ---------Daily Constraint---------

# 10. On the same day it is not possible to have two lessons of the same teaching
def repeat_teaching(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.repeat_teaching = pyo.ConstraintList()
    for day in days_:
        for course in school.course_classes:
            for teaching in course.teachings:
                model.repeat_teaching.add(
                    sum(model.x[day, hour, course.name, teaching.name] for hour in hours_)
                    <= 1
                )
    print("10. On the same day it is not possible to have two lessons of the same teaching")
    return model.repeat_teaching

# 11. If there's one lecture in the day, there must be at least another one of the same course
def student_presence(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.student_presence = pyo.ConstraintList()
    for day in days_:
        for course in school.course_classes:
            if sum([teaching.frequency for teaching in course.teachings]) >= 6:
                for teaching in course.teachings:
                    model.student_presence.add(
                        sum(
                            model.x[day, hour, course.name, teaching.name]
                            for hour in hours_
                        )
                        <= sum(
                            model.x[day, hour, course.name, other_t.name]
                            for hour in hours_
                            for other_t in course.teachings
                            if other_t != teaching
                        )
                    )
            else:
                pyo.Constraint.Skip
    print("11. If there's one lecture in the day, there must be at least another one of the same course")
    return model.student_presence

# 12. If there's one lecture in the day, there must be at least another one of the same professor
def professor_presence(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.professor_presence = pyo.ConstraintList()
    for day in days_:
        for teacher in school.teacher_classes:
            if sum([teaching.frequency for teaching in teacher.teachings]) >= 6:
                for teaching in teacher.teachings:
                    model.professor_presence.add(
                        sum(
                            model.y[day, hour, teacher.name, teaching.name]
                            for hour in hours_
                        )
                        <= sum(
                            model.y[day, hour, teacher.name, other_t.name]
                            for hour in hours_
                            for other_t in teacher.teachings
                            if other_t != teaching
                        )
                    )
            else:
                pyo.Constraint.Skip
    print("12. If there's one lecture in the day, there must be at least another one of the same professor")
    return model.professor_presence

# ---------Optional Constraints---------

# 13. There must be at least the number of free room set in parameter for each hour
def free_room(model, sets, school, parameters):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.free_room = pyo.ConstraintList()
    for day in days_:
        for hour in hours_:
            model.free_room.add(
                sum(
                    model.z[day, hour, teaching.name, room.name]
                    for teaching in school.teaching_classes
                    for room in school.room_classes
                )
                <= len(rooms_) - parameters[3]
            )
    print("13. There must be at least the number of free room set in parameter for each hour")
    return model.free_room

# # 14. Max hours per day for each course
# model.max_hours_per_day=pyo.ConstraintList()
# for day in days_:
#     for course in courses:


#             if course.partition == "NO":
#                 for teaching in course.teachings:
#                     if teaching.elective == "Obbligatorio":
#                         model.ubiquity_stud.add(
#                             sum(
#                                 model.x[day, hour, course.name, teaching.name]
#                                 for teaching in course.teachings
#                                 if teaching.elective == "Obbligatorio"
#                             )
#                             <= 1
#                         )
#                     else:
#                         model.ubiquity_stud.add(
#                             sum(
#                                 model.x[day, hour, course.name, teaching.name]
#                                 for teaching in course.teachings
#                                 if teaching.elective != "Obbligatorio"
#                             )
#                             <= 3
#                         )
#             else:
#                 for partition in course.partition:
#                     for teaching in course.teachings:
#                         if teaching.partition == partition:
#                             if teaching.elective == "Obbligatorio":
#                                 model.ubiquity_stud.add(
#                                     sum(
#                                         model.x[day, hour, course.name, teaching.name]
#                                         for teaching in course.teachings
#                                         if teaching.elective == "Obbligatorio"
#                                     )
#                                     <= 1
#                                 )
#                             else:
#                                 model.ubiquity_stud.add(
#                                     sum(
#                                         model.x[day, hour, course.name, teaching.name]
#                                         for teaching in course.teachings
#                                         if teaching.elective != "Obbligatorio"
#                                     )
#                                     <= 3
#                                     * (
#                                         1
#                                         - sum(
#                                             model.x[
#                                                 day, hour, course.name, teaching.name
#                                             ]
#                                             for teaching in course.teachings
#                                             if teaching.elective == "Obbligatorio"
#                                         )
#                                     )
#                                 )


# for day in days:
#     for c in courses:
#         if c in ct_man_no:
#             model.max_hours_per_day.add(sum(model.x[d,h,c,t] for h in hours for t in ct_man_no[c])<=max_h_daily)
#         elif c in ct_man_par:
#             for par in ct_man_par[c]:
#                 model.max_hours_per_day.add(sum(model.x[d,h,c,t] for h in hours for t in ct_man_par[c][par])<=max_h_daily)
#         elif c in ct_ele and c not in ct_man:
#             model.max_hours_per_day.add(sum(model.x[d,h,c,t] for h in hours for t in ct_ele[c])<=max_h_daily*max_elective_overlap)


# 15. Max hours per day for each professor
def professor_limit(model, sets, school):
    days_, hours_, rooms_, teachings_, courses_, teachers_ = unpack_sets(sets)
    model.professor_limit = pyo.ConstraintList()
    for day in days_:
        for teacher in school.teacher_classes:
            model.professor_limit.add(
                sum(
                    model.y[day, hour, teacher.name, teaching.name]
                    for hour in hours_
                    for teaching in teacher.teachings
                )
                <= 3
            )
    print("15. Max hours per day for each professor")
    return model.professor_limit

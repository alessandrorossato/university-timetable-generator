import pandas as pd
import itertools
import random


class BaseClass:
    def __repr__(self):
        return f"{', '.join(f'{key}={value}' for key, value in self.__dict__.items())}"

    @classmethod
    def from_data(cls, data):
        data = cls(**data)
        return data

    @classmethod
    def read_class(cls, filename):
        data = pd.read_csv(filename)
        instances = [cls.from_data(row) for _, row in data.iterrows()]
        return instances

    @staticmethod
    def filter_by(objects, attribute, parameter_list):
        instances_to_remove = [
            instance
            for instance in objects
            if getattr(instance, attribute) not in parameter_list
        ]

        for instance in instances_to_remove:
            objects.remove(instance)

        return objects


class TeachingClass(BaseClass):
    all = []

    def __init__(self, name, course, teacher, campus, partition, period, elective, frequency, size):
        self.name = name
        self.course = course
        self.teacher = teacher
        self.campus = campus
        self.partition = partition
        self.period = period
        self.elective = elective
        self.frequency = frequency
        self.size = size
        TeachingClass.all.append(self)

    @classmethod
    def from_data(cls, data):
        teachings = cls(
            name=data["Teachings"],
            course=data["Course_ID"],
            teacher=data["Professor"],
            campus=data["CAMPUS"],
            partition=data["Partition"],
            period=data["Period"],
            elective=data["grappolo"],
            frequency=data["k"],
            size=data["room_size"],            
        )
        return teachings


class CourseClass(BaseClass):
    all = []

    def __init__(self, name, teachings, partition, year, campus, size):
        self.name = name
        self.teachings = teachings
        self.partition = partition
        self.year = year
        self.campus = campus
        self.size = size
        CourseClass.all.append(self)

    @classmethod
    def read_class(cls, filename):
        data = pd.read_csv(filename)
        grouped_course = (
            data.groupby(["Course_ID", "Partition"])
            # data.groupby("Course_ID")
            .agg(
                {
                    "Teachings": list,
                    "Anno": "first",
                    "CAMPUS": "first",
                    "room_size": "first",
                }
            )
            .reset_index()
        )
        instances = [cls.from_data(row) for _, row in grouped_course.iterrows()]
        return instances

    @classmethod
    def from_data(cls, data):
        teachings = [
            teaching
            for teaching in TeachingClass.all
            if teaching.name in data["Teachings"]
        ]

        courses = cls(
            name=data["Course_ID"],
            teachings=teachings,
            partition=data["Partition"],
            year=data["Anno"],
            campus=data["CAMPUS"],
            size=data["room_size"],
        )
        return courses


class TeacherClass(BaseClass):
    all = []

    def __init__(self, name, teachings, courses, seniority, profile=None):
        self.name = name
        self.teachings = teachings
        self.courses = courses
        self.seniority = seniority
        self.profile = profile
        TeacherClass.all.append(self)

    @classmethod
    def read_class(cls, filename):
        data = pd.read_csv(filename)
        grouped_teachings = (
            data.groupby("Professor")
            .agg({"Teachings": list, "qualifica": "first"})
            .reset_index()
        )
        grouped_courses = (
            data.groupby("Professor").agg({"Course_ID": list}).reset_index()
        )
        grouped_teachings["Course_ID"] = grouped_courses["Course_ID"]
        instances = [cls.from_data(row) for _, row in grouped_teachings.iterrows()]
        return instances

    @classmethod
    def from_data(cls, data):
        teachings = [
            teaching
            for teaching in TeachingClass.all
            if teaching.teacher == data["Professor"]
        ]

        return cls(
            name=data["Professor"],
            teachings=teachings,
            courses=data["Course_ID"],
            seniority=data["qualifica"],
            profile=None,
        )

    @classmethod
    def assign_attributes(cls, qualifications, profiles):
        for teacher in cls.all:
            teacher.profile = profiles.index(random.choice(profiles))

            if teacher.seniority in qualifications:
                teacher.seniority = qualifications[teacher.seniority]
            else:
                teacher.seniority = 0.5
        return cls.all


class CalendarClass(BaseClass):
    all = []

    def __init__(self, period, day, hour, cost=1.0):
        self.period = period
        self.day = day
        self.hour = hour
        self.cost = cost
        CalendarClass.all.append(self)

    @classmethod
    def define_calendar(
        cls, n_period, n_days, n_hours, cost=1.0
    ):  # read from file also an option
        calendar = []
        for period, day, hour in itertools.product(
            range(1, n_period + 1), range(1, n_days + 1), range(1, n_hours + 1)
        ):
            cost = 1.0
            if day == 6:
                cost *= 50
            if hour == 6:
                cost *= 50
            if hour == 5:
                cost *= 10
            calendar.append(cls(period, day, hour, cost))
        return calendar


class RoomClass(BaseClass):
    all = []

    def __init__(self, name, campus, size):
        self.name = name
        self.campus = campus
        self.size = size
        RoomClass.all.append(self)

    @classmethod
    def from_data(cls, data):
        return cls(name=data["room"], campus=data["campus"], size=data["room_size"])


# define parameters: period, max_room_size, max_h_daily, free_rooms_hourly, max_elective_overlap
def define_parameters(
    period,
    mode="relaxed",
):
    if mode == "relaxed":
        parameters = [period, 5, 5, 0, 2]
    elif mode == "medium":
        parameters = [period, 3, 4, 1, 1]
    elif mode == "strict":
        parameters = [period, 2, 4, 2, 0]
    elif mode == "custom":
        parameters = [
            period,
            int(input("Insert the maximum room size: ")),
            int(input("Insert the maximum hours per day: ")),
            int(input("Insert the number of free rooms per hour: ")),
        ]
    return parameters


class School:
    def __init__(self):
        self.teaching_classes = []
        self.course_classes = []
        self.teacher_classes = []
        self.room_classes = []
        self.calendar_classes = []

    def add_teaching_class(self, teaching_class):
        self.teaching_classes.append(teaching_class)

    def add_course_class(self, course_class):
        self.course_classes.append(course_class)

    def add_teacher_class(self, teacher_class):
        self.teacher_classes.append(teacher_class)
    
    def add_room_class(self, room_class):
        self.room_classes.append(room_class)
        
    def add_calendar_class(self, calendar_class):
        self.calendar_classes.append(calendar_class)

    @classmethod
    def create_school_from_data(cls, data, qualifications, profiles, rooms, calendar):
        school = cls()

        teaching_instances = TeachingClass.read_class(data)
        for teaching_instance in teaching_instances:
            school.add_teaching_class(teaching_instance)

        course_instances = CourseClass.read_class(data)
        for course_instance in course_instances:
            school.add_course_class(course_instance)

        teacher_instances = TeacherClass.read_class(data)
        for teacher_instance in teacher_instances:
            school.add_teacher_class(teacher_instance)
        TeacherClass.assign_attributes(qualifications, profiles)
        
        room_instances = RoomClass.read_class(rooms)
        for room_instance in room_instances:
            school.add_room_class(room_instance)
        
        calendar_instances = CalendarClass.define_calendar(calendar[0], calendar[1], calendar[2])
        for calendar_instance in calendar_instances:
            school.add_calendar_class(calendar_instance)

        return school
    
    def get_teachings_by_teacher(self, teacher_name):
        return [
            teaching_instance
            for teaching_instance in self.teaching_classes
            if teaching_instance.teacher == teacher_name
        ]

    def get_teachers_by_course(self, course_name):
        return [
            teacher_instance
            for teacher_instance in self.teacher_classes
            if course_name in teacher_instance.courses
        ]
    
    def get_teachings_by_course(self, course_name):
        return [
            teaching_instance
            for teaching_instance in self.teaching_classes
            if teaching_instance.course == course_name
        ]



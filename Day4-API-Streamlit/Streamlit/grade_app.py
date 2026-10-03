import streamlit as st

st.title("Grade Manager")


# Initialize student list in Streamlit session state
if "students" not in st.session_state:
    st.session_state.students = []


def get_grade(mark):
    if mark >= 90:
        return "A"
    elif mark >= 80:
        return "B"
    elif mark >= 70:
        return "C"
    elif mark >= 60:
        return "D"
    else:
        return "E"


def add_student(name, mark):
    name = name.strip()

    # Validate name
    if not name:
        st.error("Name cannot be empty.")
        return False

    if any(char.isdigit() for char in name):
        st.error("Name cannot contain numbers.")
        return False

    if any(not char.isalnum() and not char.isspace() for char in name):
        st.error("Name cannot contain special characters.")
        return False

    # Validate mark
    if mark < 0 or mark > 100:
        st.error("Mark must be between 0 and 100.")
        return False

    grade = get_grade(mark)

    # Store student in session
    st.session_state.students.append(
        (name, mark, grade)
    )

    st.success(f"Added {name} with grade {grade}.")
    return True


def show_results():
    students = st.session_state.students

    if not students:
        st.info("No students have been added yet.")
        return

    # Display student table
    st.subheader("Student Results")

    st.table(
        [
            {
                "Name": name,
                "Mark": mark,
                "Grade": grade
            }
            for name, mark, grade in students
        ]
    )

    # Calculate statistics
    marks = [mark for _, mark, _ in students]

    average = sum(marks) / len(marks)
    highest = max(marks)
    lowest = min(marks)

    # Display metrics
    col1, col2, col3 = st.columns(3)

    col1.metric("Average", f"{average:.1f}")
    col2.metric("Highest", f"{highest:g}")
    col3.metric("Lowest", f"{lowest:g}")


# -----------------------------
# Input section
# -----------------------------

st.subheader("Add Student")

with st.form("student_form"):
    name = st.text_input("Student Name")

    mark = st.number_input(
        "Mark",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=1.0
    )

    submitted = st.form_submit_button("Add Student")

    if submitted:
        add_student(name, mark)

# -----------------------------
# Results section
# -----------------------------
show_results()
import streamlit as st


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Grade Manager",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------

st.markdown(
    """
    <style>

    /* =====================================================
       Overall application
       ===================================================== */

    .stApp {
        background: linear-gradient(
            135deg,
            #faf7ff 0%,
            #f5f3ff 45%,
            #fffaf5 100%
        );
    }

    .block-container {
        max-width: 900px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }


    /* =====================================================
       Header
       ===================================================== */

    .app-header {
        text-align: center;
        padding: 0.5rem 0 1.5rem 0;
    }

    .app-header h1 {
        font-size: 2.6rem;
        margin-bottom: 0.3rem;
        font-weight: 750;

        background: linear-gradient(
            90deg,
            #4f46e5,
            #7c3aed,
            #9333ea
        );

        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .app-header p {
        color: #6b5f7a;
        font-size: 1.05rem;
        margin-top: 0;
    }


    /* =====================================================
       Section headings
       ===================================================== */

    .section-title {
        font-size: 1.2rem;
        font-weight: 650;

        color: #312e81;

        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
    }


    /* =====================================================
       Input area
       ===================================================== */

    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.75);

        border: 1px solid #ddd6fe;

        border-radius: 14px;

        padding: 1.1rem;

        box-shadow:
            0 4px 15px rgba(79, 70, 229, 0.06);
    }


    /* Input labels */

    div[data-testid="stTextInput"] label,
    div[data-testid="stNumberInput"] label {
        color: #4c1d95 !important;
        font-weight: 600;
    }


    /* Text / number inputs */

    div[data-testid="stTextInput"] input,
    div[data-testid="stNumberInput"] input {

        background-color: #faf8ff;

        border: 1px solid #c4b5fd;

        border-radius: 8px;

        color: #312e81;

    }

    div[data-testid="stTextInput"] input:focus,
    div[data-testid="stNumberInput"] input:focus {

        border-color: #7c3aed;

        box-shadow:
            0 0 0 1px #7c3aed;

    }


    /* =====================================================
       Add button
       ===================================================== */

    div[data-testid="stFormSubmitButton"] button {

        background: linear-gradient(
            90deg,
            #6366f1,
            #7c3aed
        );

        color: white;

        border: none;

        border-radius: 9px;

        font-weight: 650;

        min-height: 2.7rem;

        box-shadow:
            0 3px 8px rgba(99, 102, 241, 0.25);

        transition: all 0.2s ease;

    }

    div[data-testid="stFormSubmitButton"] button:hover {

        background: linear-gradient(
            90deg,
            #4f46e5,
            #6d28d9
        );

        color: white;

        transform: translateY(-1px);

        box-shadow:
            0 5px 12px rgba(99, 102, 241, 0.3);

    }


    /* =====================================================
       Success message
       ===================================================== */

    div[data-testid="stAlert"] {

        border-radius: 9px;

    }


    /* =====================================================
       Metric cards
       ===================================================== */

    div[data-testid="stMetric"] {

        background: linear-gradient(
            145deg,
            #ffffff,
            #f5f3ff
        );

        border: 1px solid #ddd6fe;

        border-radius: 14px;

        padding: 1rem;

        box-shadow:
            0 4px 12px rgba(79, 70, 229, 0.07);

    }

    div[data-testid="stMetricLabel"] {

        color: #6366f1;

        font-size: 0.9rem;

        font-weight: 600;

    }

    div[data-testid="stMetricValue"] {

        color: #312e81;

        font-size: 1.9rem;

        font-weight: 750;

    }


    /* =====================================================
       Results table container
       ===================================================== */

    div[data-testid="stDataFrame"] {

        border:

            1px solid #ddd6fe;

        border-radius: 12px;

        overflow: hidden;

        box-shadow:
            0 3px 10px rgba(79, 70, 229, 0.05);

    }


    /* =====================================================
       Empty state
       ===================================================== */

    .empty-state {

        text-align: center;

        padding: 2rem 1rem;

        border: 1px dashed #c4b5fd;

        border-radius: 14px;

        background: linear-gradient(
            135deg,
            #faf5ff,
            #f5f3ff
        );

        color: #6b5f7a;

    }

    .empty-state-icon {

        font-size: 2.5rem;

        margin-bottom: 0.5rem;

    }


    /* =====================================================
       Footer
       ===================================================== */

    .footer {

        text-align: center;

        color: #8b7fa1;

        font-size: 0.8rem;

        margin-top: 2.5rem;

    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "students" not in st.session_state:
    st.session_state.students = []


# ---------------------------------------------------------
# Business logic
# ---------------------------------------------------------

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
        st.error("Please enter a student name.")
        return False

    if any(char.isdigit() for char in name):
        st.error("Student name cannot contain numbers.")
        return False

    if any(
        not char.isalnum() and not char.isspace()
        for char in name
    ):
        st.error("Student name cannot contain special characters.")
        return False

    # Validate mark
    if mark < 0 or mark > 100:
        st.error("Mark must be between 0 and 100.")
        return False

    grade = get_grade(mark)

    st.session_state.students.append(
        (name, mark, grade)
    )

    return True


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    """
    <div class="app-header">
        <h1>🎓 Grade Manager</h1>
        <p>Track student marks and class performance</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Add student
# ---------------------------------------------------------

st.markdown(
    '<div class="section-title">Add Student</div>',
    unsafe_allow_html=True,
)

with st.form("student_form", clear_on_submit=True):

    col1, col2 = st.columns([2, 1])

    with col1:
        name = st.text_input(
            "Student Name",
            placeholder="e.g. Priya",
        )

    with col2:
        mark = st.number_input(
            "Mark",
            min_value=1,
            max_value=100,
            value=1,
            step=1,
        )

    submitted = st.form_submit_button(
        "➕  Add Student",
        use_container_width=True,
    )

    if submitted:

        if add_student(name, mark):
            st.success(
                f"✓ {name.strip()} added successfully."
            )


# ---------------------------------------------------------
# Results
# ---------------------------------------------------------

students = st.session_state.students

st.markdown(
    '<div class="section-title">Class Overview</div>',
    unsafe_allow_html=True,
)


if not students:

    st.markdown(
        """
        <div class="empty-state">
            <div class="empty-state-icon">📚</div>
            <strong>No students yet</strong><br>
            Add a student above to see the class results.
        </div>
        """,
        unsafe_allow_html=True,
    )

else:

    # ---------------------------------------------
    # Statistics
    # ---------------------------------------------

    marks = [
        mark
        for _, mark, _ in students
    ]

    average = sum(marks) / len(marks)
    highest = max(marks)
    lowest = min(marks)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Average",
            f"{average:.1f}",
        )

    with col2:
        st.metric(
            "Highest",
            f"{highest:g}",
        )

    with col3:
        st.metric(
            "Lowest",
            f"{lowest:g}",
        )

    # ---------------------------------------------
    # Student table
    # ---------------------------------------------

    st.markdown(
        '<div class="section-title">Student Results</div>',
        unsafe_allow_html=True,
    )

    table_data = []

    for name, mark, grade in students:
        table_data.append(
            {
                "Name": name,
                "Mark": mark,
                "Grade": grade,
            }
        )

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn(
                "Student Name",
                width="medium",
            ),
            "Mark": st.column_config.NumberColumn(
                "Mark",
                format="%.1f",
            ),
            "Grade": st.column_config.TextColumn(
                "Grade",
                width="small",
            ),
        },
    )


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.markdown(
    """
    <div class="footer">
        Grade Manager • Built with Python & Streamlit
    </div>
    """,
    unsafe_allow_html=True,
)
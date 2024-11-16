import sqlite3

# Create the database
conn = sqlite3.connect('habit_tracker.db')
cursor = conn.cursor()

# 1. User Database
cursor.execute('''
   CREATE TABLE IF NOT EXISTS Users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL, -- This should be hashed
    registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
    parent_id INTEGER,  -- Foreign key to parents table
    date_of_birth TEXT NOT NULL,  -- Child's date of birth
    gender TEXT,  -- Optional: to specify the child's gender,
    phone TEXT,
    FOREIGN KEY (parent_id) REFERENCES Parents(id) ON DELETE SET NULL
)
''')


cursor.execute('''
   CREATE TABLE IF NOT EXISTS Parents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL, -- This should be hashed
    registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
    phone TEXT
)
''')


# 2. Task Database - Updated without content_id reference
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        content_id INTEGER,
        user_id INTEGER,  -- User ID to track task ownership
        task_name TEXT NOT NULL,
        due_date TEXT,
        status TEXT CHECK(status IN ('Completed', 'Pending','Active')),
        completion_date TEXT,
        time_spent INTEGER,
        reward_earned TEXT,
        FOREIGN KEY(user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    )
''')

# 3. Analytics Database
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Analytics (
        analytics_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_completion_rate REAL,
        habit_progress REAL, -- Percentage of completion
        feedback TEXT,
        date_of_analysis TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    )
''')

# 4. Course Content Database
cursor.execute('''
    CREATE TABLE IF NOT EXISTS CourseContent (
        content_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        content_type TEXT CHECK(content_type IN ('Video', 'PDF', 'Assignment')),
        content_url TEXT,
        upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
        content_learning TEXT ,
        frequency TEXT CHECK(frequency IN ('Daily', 'Weekly')),
        start_date TEXT,
        end_date TEXT,
        status TEXT CHECK(status IN ('Active', 'Inactive')),
        completion_percentage INTEGER DEFAULT 0,
        user_id INTEGER NOT NULL,  -- Added user_id for referencing Users table
        FOREIGN KEY(user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    )
''')




# 2. Habit Database
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Habits (
        habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER  NULL,
        habit_name TEXT NOT NULL,
        content_id INTEGER ,
        description TEXT,
        frequency TEXT CHECK(frequency IN ('Daily', 'Weekly')),
        start_date TEXT,
        end_date TEXT,
        status TEXT CHECK(status IN ('Active', 'Inactive','Completed')),
        FOREIGN KEY(user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    )
''')


# 5. Assessment Database
cursor.execute('''
CREATE TABLE IF NOT EXISTS Assessments (
    assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER,
    question TEXT,
    option1 TEXT,
    option2 TEXT,
    option3 TEXT,
    option4 TEXT,
    correct_option TEXT,
    FOREIGN KEY(course_id) REFERENCES CourseContent(course_id) ON DELETE CASCADE
)
''')

# 6. Goals Database
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Goals (
        goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        goal_description TEXT NOT NULL,
        target_date TEXT NOT NULL,
        status TEXT CHECK(status IN ('Active', 'Achieved', 'Pending', 'Failed','Completed')) DEFAULT 'Active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    )
''')


cursor.execute('''
CREATE TABLE HabitProgress (
    progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    content_id INTEGER NOT NULL, -- References habit_id in the Habits table
    title TEXT NOT NULL,
    time_spent INTEGER,
    last_assessment_score INTEGER DEFAULT 0.0, -- Score percentage for the last assessment taken
    progress_level INTEGER DEFAULT 0, -- Level or milestone achieved in the habit
    rewards_earned TEXT, -- Stores the latest reward earned, e.g., "Gold Star", "Silver Star"
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Date when this record was last updated
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (content_id) REFERENCES Habits(habit_id),
    UNIQUE (user_id, content_id) -- Ensures only one progress record per user and habit
)
''')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database and tables created successfully.")

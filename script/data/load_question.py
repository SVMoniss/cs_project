import csv
import sqlite3

# Connect to SQLite database (or create it if it doesn't exist)
connection = sqlite3.connect('question_bank.db')

# Create a cursor object to execute SQL queries
cursor = connection.cursor()

# Create tables if they don't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS Levels (
    level_name TEXT NOT NULL,
    complexity INTEGER PRIMARY KEY
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS TestPapers (
    paper_id INTEGER PRIMARY KEY,
    level_id INTEGER NOT NULL,
    paper_name TEXT NOT NULL,
    FOREIGN KEY (level_id) REFERENCES Levels(complexity)
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    correct_answer_id INTEGER NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES TestPapers(paper_id)
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS Options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_text TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (question_id) REFERENCES Questions(id)
);
''')

# Function to import data from CSV
def import_csv_to_db(file_path):
    with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
        csvreader = csv.DictReader(csvfile)
        
        for row in csvreader:
            level = int(row['level'])
            paper_id = int(row['paper_id'])
            question_text = row['question_text']
            options = [
                row['option_1'],
                row['option_2'],
                row['option_3'],
                row['option_4']
            ]
            correct_option = int(row['correct_option']) - 1  # Convert to 0-based index
            
            # Insert or get level ID
            cursor.execute("INSERT OR IGNORE INTO Levels (level_name, complexity) VALUES (?, ?)", 
                           (f"Level {level}", level))
            cursor.execute("SELECT complexity FROM Levels WHERE level_name = ?", (f"Level {level}",))
            level_id = cursor.fetchone()[0]
            result = cursor.fetchone()
	


            # Insert or get paper ID
            cursor.execute("INSERT OR IGNORE INTO TestPapers (paper_id, level_id, paper_name) VALUES (?, ?, ?)", 
                           ((level_id*100) + paper_id , level_id, f"Paper {paper_id}"))



            # Get the last inserted paper ID
            cursor.execute("SELECT paper_id FROM TestPapers WHERE level_id = ? AND paper_name = ?", 
                           (level_id, f"Paper {paper_id}"))
            paper_db_id = cursor.fetchone()[0]

            # Insert question and options
            cursor.execute("INSERT INTO Questions (paper_id, question_text, correct_answer_id) VALUES (?, ?, ?)", 
                           (paper_db_id, question_text, correct_option + 1))  # Store correct answer as 1-based index
            
            question_db_id = cursor.lastrowid
            
            for idx, option in enumerate(options):
                cursor.execute("INSERT INTO Options (question_id, option_text, is_correct) VALUES (?, ?, ?)", 
                               (question_db_id, option, idx == correct_option))

# Specify your CSV file path here
csv_file_path = 'questions.csv'
import_csv_to_db(csv_file_path)

# Commit the changes and close the connection
connection.commit()
connection.close()

print("Data imported successfully!")
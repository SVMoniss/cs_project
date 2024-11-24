import sqlite3
import requests
import random
from flask import Flask, session, redirect, url_for, request, render_template, g,jsonify

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key
app.config['SESSION_TYPE'] = 'filesystem'

DATABASE = 'users.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Return rows as dictionaries
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        # Create users table
        db.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)')
        # Create user_progress table
        db.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                username TEXT,
                level INTEGER,
                score INTEGER,
                completed BOOLEAN,
                PRIMARY KEY (username, level),
                FOREIGN KEY (username) REFERENCES users (username)
            )
        ''')
        db.commit()

def fetch_questions(level):
    # Define complexity based on level
    complexity_map = {
        1: 'easy',
        2: 'medium',
        3: 'medium',
        4: 'hard',
        5: 'hard'
    }
    
    complexity = complexity_map.get(level, 'easy')  # Default to easy if level not found

    # Replace 'YOUR_API_KEY' with your actual Perplexity API key
    headers = {
        'Authorization': 'Bearer YOUR_API_KEY',
    }
    
        # Fetch 10 questions based on complexity
    response = requests.get(f'https://api.perplexity.ai/v1/questions/general-knowledge?complexity={complexity}&limit=10', headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        questions = []
        
        for item in data['questions']:
            question_text = item['question']
            options = item['options']
            correct_answer = item['correct_answer']  # Assuming the API returns this field
            
            questions.append({
                'question': question_text,
                'options': options,
                'correct_answer': correct_answer
            })
        
        return questions
    else:
        return "Error fetching questions", []

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('game'))
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            db = get_db()
            db.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return 'User already exists! <a href="/register">Try again</a>'
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        if user:
            session['username'] = username
            return redirect(url_for('game'))
        return 'Invalid credentials! <a href="/login">Try again</a>'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/game')
def game():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    db = get_db()
    
    # Get user's progress
    levels = {}
    for level in range(1, 6):
        progress = db.execute('SELECT * FROM user_progress WHERE username = ? AND level = ?', (username, level)).fetchone()
        levels[level] = {
            'completed': progress['completed'] if progress else False,
            'score': progress['score'] if progress else 0
        }
    
    return render_template('game.html', username=username, levels=levels)

def get_random_paper_id(level):
    print(level)
    conn = sqlite3.connect('question_bank.db')
    cursor = conn.cursor()
    paper_name = 'Paper '  + str(level)
    # Select a random paper ID for the given level
    cursor.execute('''
        SELECT paper_id FROM TestPapers WHERE level_id = ?  and paper_name = ?
    ''', (level, paper_name,))
    
    papers = cursor.fetchall()
    
    if not papers:
        return None  # No papers found for this level

    # Select a random paper ID from the available ones
    random_paper = random.choice(papers)
    conn.close()
    
    return random_paper[0]  # Return the paper 

def get_questions(paper_id):
    conn = sqlite3.connect('question_bank.db')
    cursor = conn.cursor()

    # Fetch questions for the given paper ID
    cursor.execute('''
        SELECT q.id, q.question_text, o.option_text, o.id AS option_id
        FROM Questions q
        JOIN Options o ON q.id = o.question_id
        WHERE q.paper_id = ?
    ''', (paper_id,))
    
    questions = cursor.fetchall()
    
    # Organize questions into a structured format
    question_data = {}
    for question_id, question_text, option_text, option_id in questions:
        print(question_id)
        if question_id not in question_data:
            question_data[question_id] = {
                'id': question_id,
                'question_text': question_text,
                'options': [],
                'correct_option': None  # Placeholder for correct answer
            }
        question_data[question_id]['options'].append({
            'option_text': option_text,
            'option_id': option_id
        })

    conn.close()
    
    return list(question_data.values())  # Return as a list of questions


@app.route('/level/<int:level>', methods=['GET', 'POST'])
def level(level):
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    
    # Check if the previous level is completed before allowing access
    previous_level_completed = True if level == 1 else \
                               bool(get_db().execute('SELECT completed FROM user_progress WHERE username = ? AND level = ?', 
                                               (username, level - 1)).fetchone())

    if not previous_level_completed:
        #return f'<h1>You must complete Level {level - 1} first!</h1><p><a href="/game">Back to Treasure Map</a></p>'
        return render_template('pre-level.html', level=level)
    
    if request.method == 'POST':
        total_score = 0
        
        for i in range(10):  # Assuming there are always 10 questions
            selected_answer = request.form.get(f'answer_{i}')
            correct_answer = request.form.get(f'correct_answer_{i}')
            
            if selected_answer == correct_answer:
                total_score += 10  # Add points for correct answer
        
        # Store score and mark level as completed
        db = get_db()
        db.execute('INSERT OR REPLACE INTO user_progress (username, level, score, completed) VALUES (?, ?, ?, ?)',
                   (username, level, total_score, True))
        db.commit()
        
        return redirect(url_for('game'))

    #if 'user_level' not in session:
    session['user_level'] = level  # Set user level in session
    session['answers'] = []

    paper_id = get_random_paper_id(level)
    
    if not paper_id:
        return jsonify({"message": "No papers available for this level."}), 404
    
    questions = get_questions(paper_id)
    print(questions)
    return render_template('questions.html', questions=questions)

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()  # Get JSON data from the request
    
    if not data or 'answers' not in data:
        return jsonify({"message": "No answers submitted."}), 400
    
    answers = data['answers']  # Extract answers from the request data
    
    score = 0
    
    conn = sqlite3.connect('question_bank.db')
    cursor = conn.cursor()

    for answer in answers:
        cursor.execute('''
            SELECT correct_answer_id FROM Questions WHERE id = ?
        ''', (answer['question_id'],))
        
        correct_answer_id = cursor.fetchone()
        
        if correct_answer_id and answer['option_id'] == correct_answer_id[0]:
            score += 1

    total_questions = len(answers)
    conn.close()

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Determine feedback color based on score
    feedback_color = ""
    next_level_allowed = False
   
    if score > 5:  # If score is greater than 5, allow next level and set color to green
        feedback_color = "green"
        next_level_allowed = True
        
        print(session['user_level'])
        # Update user's completed levels in the database (assuming user ID is stored in session)
        cursor.execute('INSERT OR REPLACE INTO user_progress (username, level, score, completed) VALUES (?, ?, ?, ?)',
                   (session['username'],  session['user_level'] , score, True))
        session['user_level'] += 1  # Allow progression to the next level
    elif score >= total_questions * 0.5:  # Between 50% and 80% is orange
        feedback_color = "orange"
    else:  # Less than 50% is red
        feedback_color = "red"

    conn.commit()  # Commit changes to the database
    conn.close()

    return jsonify({
        "score": score,
        "total": total_questions,
        "feedback_color": feedback_color,
        "next_level_allowed": next_level_allowed,
        "current_level": session['user_level']  # Return current level after submission
    })

@app.route('/reset', methods=['POST'])
def reset():
   session.pop('user_level', None)  # Reset user level progress
   return jsonify({"message": "User progress reset."}), 200

if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)

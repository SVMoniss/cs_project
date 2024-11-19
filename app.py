import sqlite3
import requests
from flask import Flask, session, redirect, url_for, request, render_template, g

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
    return '<h1>Welcome! <a href="/login">Login</a> or <a href="/register">Register</a></h1>'

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
        return f'<h1>You must complete Level {level - 1} first!</h1><p><a href="/game">Back to Treasure Map</a></p>'
    
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

    questions = fetch_questions(level)
    
    return render_template('level.html', username=username, questions=questions)


if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)
Prerequisite:
1.	Set Up Your Local Environment:
•	Install Python and Flask on your local machine.
Python 3.13.0 - Oct. 7, 2024
Note that Python 3.13.0 cannot be used on Windows 7 or earlier.
2.	Download Windows installer (64-bit) & Ensure to install SQLlite 
•	Use SQLite for your database; it comes pre-installed with Python.
3.	Develop Your Application:
•	pip install Flask 
•	pip install requests 
•	pip install random
•	Create your Flask app with routes to serve HTML pages and handle user input.
•	Use SQLite to store user and user scores.
•	Implement the game logic in Python.
4. Create question_bank.db, 
cd scripts/data/
python load_question.py 
5. Ensure question_bank.db is created
6. Now from cs_project folder, run the Python Flask Web App
python app.py
7. If no error, open the web app, in browser http://127.0.0.1:5000/

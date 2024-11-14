import sqlite3
from wsgiref.simple_server import make_server
import json
from urllib.parse import parse_qs

# Initialize SQLite3 database
DB_PATH = 'skills.db'

# Function to create the database if it doesn't exist
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Create skills table if not exists
        cursor.execute('''CREATE TABLE IF NOT EXISTS skills (
                            id INTEGER PRIMARY KEY,
                            name TEXT UNIQUE NOT NULL,
                            need INTEGER NOT NULL,
                            have INTEGER NOT NULL)''')
        conn.commit()

# Application logic
def application(environ, start_response):
    init_db()  # Ensure the database is initialized

    # Parse the URL path
    path = environ.get('PATH_INFO', '').lstrip('/')

    # Set headers for response
    headers = [('Content-type', 'text/html')]
    start_response('200 OK', headers)

    if path == 'skills':
        # Fetch the skills and their levels from the database
        return [generate_skill_page().encode('utf-8')]

    elif path.startswith('update_need') or path.startswith('update_have'):
        # Update the "need" or "have" counters
        parts = path.split('/')
        skill_name = parts[1]
        action = parts[2] if len(parts) > 2 else 'increment'
        counter_type = 'need' if path.startswith('update_need') else 'have'
        
        if skill_name in [skill['name'] for skill in get_skills()]:
            if action == 'increment':
                update_counter(skill_name, counter_type, 1)
            elif action == 'decrement':
                update_counter(skill_name, counter_type, -1)
        
        # Return a simple success message
        return [b"Counter updated successfully!"]

    elif path == 'add_skill':
        # Add a new skill to the database
        skill_name = parse_qs(environ.get('QUERY_STRING', '')).get('skill', [None])[0]
        if skill_name:
            add_skill_to_db(skill_name)
            return [b"Skill added successfully!"]

    return [b"Not found"]

# Function to get the list of skills from the database
def get_skills():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name, need, have FROM skills')
        skills = cursor.fetchall()
        return [{"name": skill[0], "need": skill[1], "have": skill[2]} for skill in skills]

# Function to add a new skill to the database
def add_skill_to_db(skill_name):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO skills (name, need, have) VALUES (?, 0, 0)', (skill_name,))
        conn.commit()

# Function to update a "need" or "have" counter
def update_counter(skill_name, counter_type, delta):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f'UPDATE skills SET {counter_type} = {counter_type} + ? WHERE name = ?', (delta, skill_name))
        conn.commit()

# Generate the HTML page with skills and actions
def generate_skill_page():
    skills = get_skills()
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reverse Job Board</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                padding: 20px;
            }
            .skill-list {
                list-style-type: none;
                padding: 0;
            }
            .skill-item {
                margin: 10px 0;
                padding: 10px;
                background-color: #f4f4f4;
                border-radius: 5px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .counter-button {
                padding: 5px 10px;
                margin: 0 5px;
                cursor: pointer;
                border: none;
                background-color: #28a745;
                color: white;
                border-radius: 3px;
            }
            .counter-button:hover {
                background-color: #218838;
            }
            .add-skill-form {
                margin-top: 20px;
            }
            .add-skill-form input {
                padding: 5px;
                font-size: 14px;
            }
            .add-skill-form button {
                padding: 5px 10px;
                margin-left: 10px;
                cursor: pointer;
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <h1>Reverse Job Board</h1>
        <h2>Skills</h2>
        <ul id="skills-list" class="skill-list">
    """
    
    for skill in skills:
        html_content += f"""
        <li class="skill-item" id="skill-{skill['name']}">
            <span>{skill['name']}</span>
            <div>
                <span>Need: <span id="need-{skill['name']}">{skill['need']}</span></span>
                <button class="counter-button" onclick="updateCounter('{skill['name']}', 'need', 'increment')">+</button>
                <button class="counter-button" onclick="updateCounter('{skill['name']}', 'need', 'decrement')">-</button>
                <span>Have: <span id="have-{skill['name']}">{skill['have']}</span></span>
                <button class="counter-button" onclick="updateCounter('{skill['name']}', 'have', 'increment')">+</button>
                <button class="counter-button" onclick="updateCounter('{skill['name']}', 'have', 'decrement')">-</button>
            </div>
        </li>
        """
    
    html_content += """
        </ul>

        <div id="message"></div>

        <div class="add-skill-form">
            <input type="text" id="new-skill" placeholder="Enter a new skill" />
            <button onclick="addSkill()">Add Skill</button>
        </div>

        <script>
            // Update skill "need" or "have"
            function updateCounter(skillName, counterType, action) {
                fetch(`/update_${counterType}/${skillName}/${action}`)
                    .then(response => response.text())
                    .then(message => {
                        document.getElementById('message').innerText = message;
                        
                        // Update the counter on the page live
                        const counterElement = document.getElementById(counterType + '-' + skillName);
                        let currentValue = parseInt(counterElement.innerText);
                        currentValue = (action === 'increment') ? currentValue + 1 : currentValue - 1;
                        counterElement.innerText = currentValue;
                    });
            }

            // Add a new skill
            function addSkill() {
                const skillName = document.getElementById('new-skill').value.trim();
                if (skillName) {
                    fetch(`/add_skill?skill=${encodeURIComponent(skillName)}`)
                        .then(response => response.text())
                        .then(message => {
                            document.getElementById('message').innerText = message;

                            const skillList = document.getElementById('skills-list');
                            const newSkillItem = document.createElement('li');
                            newSkillItem.classList.add('skill-item');
                            newSkillItem.innerHTML = `
                                <span>${skillName}</span>
                                <div>
                                    <span>Need: <span id="need-${skillName}">0</span></span>
                                    <button class="counter-button" onclick="updateCounter('${skillName}', 'need', 'increment')">+</button>
                                    <button class="counter-button" onclick="updateCounter('${skillName}', 'need', 'decrement')">-</button>
                                    <span>Have: <span id="have-${skillName}">0</span></span>
                                    <button class="counter-button" onclick="updateCounter('${skillName}', 'have', 'increment')">+</button>
                                    <button class="counter-button" onclick="updateCounter('${skillName}', 'have', 'decrement')">-</button>
                                </div>
                            `;
                            skillList.appendChild(newSkillItem);

                            // Clear the input field after adding the skill
                            document.getElementById('new-skill').value = '';
                        });
                }
            }
        </script>
    </body>
    </html>
    """
    
    return html_content

# Start the WSGI server
if __name__ == "__main__":
    httpd = make_server('', 8000, application)
    print("Serving on port 8000...")
    httpd.serve_forever()

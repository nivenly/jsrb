import psycopg2
from flask import Flask, request, render_template_string, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import random
import os

app = Flask(__name__)

# Function to read the config from the 'config.env' file
def load_config():
    config = {}
    with open('config.env', 'r') as f:
        for line in f.readlines():
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value
    return config

# Load configuration from config.env
config = load_config()

# PostgreSQL database connection
def get_db_connection():
    conn = psycopg2.connect(
        dbname=config.get('DB_NAME', 'rjb'),
        user=config.get('DB_USER', 'quinn'),
        password=config.get('DB_PASSWORD', 'nivenly'),
        host=config.get('DB_HOST', 'localhost')
    )
    return conn

# Initialize the database
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Creating the tables if not exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        email VARCHAR(100) NOT NULL,
        password VARCHAR(100) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS skills (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        need INT DEFAULT 0,
        have INT DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS user_skills (
        user_id INT REFERENCES users(id) ON DELETE CASCADE,
        skill_id INT REFERENCES skills(id) ON DELETE CASCADE,
        PRIMARY KEY (user_id, skill_id)
    );

    CREATE TABLE IF NOT EXISTS projects (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS project_skills (
        project_id INT REFERENCES projects(id) ON DELETE CASCADE,
        skill_id INT REFERENCES skills(id) ON DELETE CASCADE,
        PRIMARY KEY (project_id, skill_id)
    );
    ''')
    conn.commit()
    conn.close()

# Populate 'have' column with user skills
def update_have_column():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Reset the 'have' column to 0 for all skills
    cursor.execute('UPDATE skills SET have = 0')

    # Count how many users have each skill and update the 'have' column
    cursor.execute('''
        INSERT INTO skills (name, have)
        SELECT s.name, COUNT(us.user_id)
        FROM user_skills us
        JOIN skills s ON us.skill_id = s.id
        GROUP BY s.name
        ON CONFLICT (name) DO UPDATE SET have = EXCLUDED.have;
    ''')

    conn.commit()
    conn.close()

# Populate 'need' column based on project skills
def update_need_column():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Reset the 'need' column to 0 for all skills
    cursor.execute('UPDATE skills SET need = 0')

    # Count how many projects require each skill and update the 'need' column
    cursor.execute('''
        INSERT INTO skills (name, need)
        SELECT s.name, COUNT(ps.project_id)
        FROM project_skills ps
        JOIN skills s ON ps.skill_id = s.id
        GROUP BY s.name
        ON CONFLICT (name) DO UPDATE SET need = EXCLUDED.need;
    ''')

    conn.commit()
    conn.close()

# Display all users and their skills at /skills
@app.route('/skills', methods=['GET'])
def show_skills():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT users.id, users.username, skills.name FROM users '
                   'JOIN user_skills ON users.id = user_skills.user_id '
                   'JOIN skills ON user_skills.skill_id = skills.id')
    
    user_skills = cursor.fetchall()

    skills_dict = {}
    for user_id, username, skill in user_skills:
        if user_id not in skills_dict:
            skills_dict[user_id] = {"username": username, "skills": []}
        skills_dict[user_id]["skills"].append(skill)

    cursor.execute('SELECT name, need, have FROM skills')
    skills_table = cursor.fetchall()

    # Fetch all projects
    cursor.execute('SELECT p.name, p.description, s.name FROM projects p '
                   'JOIN project_skills ps ON p.id = ps.project_id '
                   'JOIN skills s ON ps.skill_id = s.id')
    project_skills = cursor.fetchall()

    # Organize project skills
    project_dict = {}
    for project_name, project_desc, skill_name in project_skills:
        if project_name not in project_dict:
            project_dict[project_name] = {"description": project_desc, "skills": []}
        project_dict[project_name]["skills"].append(skill_name)

    conn.close()

    inline_css = """
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }
        h1 { font-size: 2.5em; color: #2c3e50; }
        .user-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
        .user-card { background-color: #fff; padding: 15px; text-align: center; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); }
        .skills-list { list-style-type: none; padding: 0; }
        .skills-list li { margin: 5px 0; }
        table { width: 100%; margin-top: 40px; border-collapse: collapse; }
        table, th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; }
        a { text-decoration: none; color: #2980b9; font-weight: bold; }
        a:hover { text-decoration: underline; }

        /* Styling for projects */
        .project-list {
            margin-top: 40px;
        }

        .project-card {
            background-color: #fff;
            padding: 15px;
            margin-bottom: 20px;
            text-align: left;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }

        .project-card h3 {
            font-weight: bold;
            color: #2980b9;
        }

        .project-card p {
            font-size: 1.1em;
            color: #333;
        }

        .project-card ul {
            list-style-type: none;
            padding: 0;
        }

        .project-card ul li {
            margin: 5px 0;
        }
    </style>
    """

    html_content = """
    <h1>User Skills</h1>
    <div class="user-grid">
        {% for user_id, user_data in users.items() %}
            <div class="user-card">
                <a href="{{ url_for('user_profile', user_id=user_id) }}" class="username">{{ user_data.username }}</a>
                <ul class="skills-list">
                    {% for skill in user_data.skills %}
                        <li>{{ skill }}</li>
                    {% endfor %}
                </ul>
            </div>
        {% endfor %}
    </div>

    <h2>Skills Overview</h2>
    <table>
        <thead>
            <tr>
                <th>Skill</th>
                <th>Need</th>
                <th>Have</th>
            </tr>
        </thead>
        <tbody>
            {% for skill in skills %}
                <tr>
                    <td>{{ skill[0] }}</td>
                    <td>{{ skill[1] }}</td>
                    <td>{{ skill[2] }}</td>
                </tr>
            {% endfor %}
        </tbody>
    </table>

    <h2>Projects</h2>
    <div class="project-list">
        {% for project_name, project_data in projects.items() %}
            <div class="project-card">
                <a href="{{ url_for('show_project', project_name=project_name) }}" class="project-name">
                    <h3>{{ project_name }}</h3>
                </a>
                <p>{{ project_data.description }}</p>
                <h4>Required Skills:</h4>
                <ul>
                    {% for skill in project_data.skills %}
                        <li>{{ skill }}</li>
                    {% endfor %}
                </ul>
            </div>
        {% endfor %}
    </div>
    """

    return render_template_string(inline_css + html_content, users=skills_dict, skills=skills_table, projects=project_dict)

# User Profiles
@app.route('/user/<int:user_id>', methods=['GET'])
def user_profile(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT users.username, skills.name FROM users '
                   'JOIN user_skills ON users.id = user_skills.user_id '
                   'JOIN skills ON user_skills.skill_id = skills.id '
                   'WHERE users.id = %s', (user_id,))

    user_skills = cursor.fetchall()
    conn.close()

    if not user_skills:
        return jsonify({"error": "User not found"}), 404

    username = user_skills[0][0]  # The username is the first element of the first record
    skills = [skill[1] for skill in user_skills]

    # Inline CSS for profile page
    profile_css = """
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
            color: #333;
        }

        h1 {
            font-size: 2.5em;
            color: #2c3e50;
            margin-bottom: 20px;
        }

        h2 {
            color: #2980b9;
        }

        ul {
            list-style-type: none;
            padding: 0;
        }

        ul li {
            background-color: #ecf0f1;
            margin: 5px;
            padding: 10px;
            border-radius: 5px;
        }

        a {
            text-decoration: none;
            color: #2980b9;
            font-weight: bold;
        }

        a:hover {
            text-decoration: underline;
        }
    </style>
    """

    profile_html = """
    <h1>{{ username }}'s Profile</h1>

    <h2>Skills</h2>
    <ul>
        {% for skill in skills %}
            <li>{{ skill }}</li>
        {% endfor %}
    </ul>

    <a href="{{ url_for('show_skills') }}">Back to All Users</a>
    """

    return render_template_string(profile_css + profile_html, username=username, skills=skills)


# Show individual project details
@app.route('/projects/<project_name>', methods=['GET'])
def show_project(project_name):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT p.name, p.description, s.name FROM projects p '
                   'JOIN project_skills ps ON p.id = ps.project_id '
                   'JOIN skills s ON ps.skill_id = s.id '
                   'WHERE p.name = %s', (project_name,))

    project_skills = cursor.fetchall()
    conn.close()

    if not project_skills:
        return jsonify({"error": "Project not found"}), 404

    description = project_skills[0][1]  # The project description is the second element
    skills = [skill[2] for skill in project_skills]

    # Inline CSS for project page
    project_css = """
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            padding: 20px;
            color: #333;
        }

        h1 {
            font-size: 2.5em;
            color: #2c3e50;
            margin-bottom: 20px;
        }

        h2 {
            color: #2980b9;
        }

        ul {
            list-style-type: none;
            padding: 0;
        }

        ul li {
            background-color: #ecf0f1;
            margin: 5px;
            padding: 10px;
            border-radius: 5px;
        }

        a {
            text-decoration: none;
            color: #2980b9;
            font-weight: bold;
        }

        a:hover {
            text-decoration: underline;
        }
    </style>
    """

    project_html = """
    <h1>{{ project_name }}</h1>

    <h2>Description</h2>
    <p>{{ description }}</p>

    <h2>Required Skills</h2>
    <ul>
        {% for skill in skills %}
            <li>{{ skill }}</li>
        {% endfor %}
    </ul>

    <a href="{{ url_for('show_skills') }}">Back to All Projects</a>
    """

    return render_template_string(project_css + project_html, project_name=project_name, description=description, skills=skills)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='127.0.0.1', port=8000)

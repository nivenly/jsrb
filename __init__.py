import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../jsrb')))

from app import app, init_db, get_skills, update_counter, add_skill_to_db

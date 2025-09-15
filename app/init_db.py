# init_db.py
from database import create_tables
import models

def init_database():
    """Initialize database"""
    print(" Creating database tables...")
    create_tables()
    print(" Database initialized!")

if __name__ == "__main__":
    init_database()
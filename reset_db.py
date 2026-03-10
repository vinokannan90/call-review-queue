"""
reset_db.py — Drop all tables and recreate fresh database schema
Run this when models have changed: python reset_db.py
Then run seed.py to populate with demo data.
"""
import os
from app import app
from models import db

def reset_database():
    with app.app_context():
        print('\n🗑️  Dropping all tables...')
        db.drop_all()
        
        print('✨ Creating fresh database schema...')
        db.create_all()
        
        print('✅ Database reset complete!')
        print('\n📝 Next step: Run "python seed.py" to populate with demo data.\n')

if __name__ == '__main__':
    # Confirm before proceeding
    response = input('⚠️  This will DELETE all data and recreate the database. Continue? (yes/no): ')
    if response.lower() in ('yes', 'y'):
        reset_database()
    else:
        print('❌ Cancelled.')

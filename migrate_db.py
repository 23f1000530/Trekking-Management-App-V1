"""
Trekk Management App — Schema Migration Script

Adds the trek/booking lifecycle columns introduced with trek status tracking
and trekking history to an existing database.

`db.create_all()` only creates missing TABLES — it will not add new COLUMNS to
tables that already exist, so an existing trekk_management.db needs this.

Safe to run more than once: each column is only added if it is missing.

Usage:
    python migrate_db.py
"""

from sqlalchemy import inspect, text

from app import create_app, db

# table -> {column: SQL type}
NEW_COLUMNS = {
    'treks': {
        'approved_at': 'DATETIME',
        'completed_at': 'DATETIME',
        'completion_notes': 'TEXT',
    },
    'bookings': {
        'completed_at': 'DATETIME',
        'cancelled_at': 'DATETIME',
    },
}


def migrate():
    """Add any missing lifecycle columns to the existing database."""
    app = create_app()

    with app.app_context():
        # Create any tables that don't exist yet
        db.create_all()

        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        added = 0

        for table, columns in NEW_COLUMNS.items():
            if table not in existing_tables:
                print(f'[SKIP] Table "{table}" does not exist yet.')
                continue

            present = {col['name'] for col in inspector.get_columns(table)}

            for column, sql_type in columns.items():
                if column in present:
                    print(f'[OK]   {table}.{column} already present.')
                    continue

                db.session.execute(
                    text(f'ALTER TABLE {table} ADD COLUMN {column} {sql_type}')
                )
                print(f'[ADD]  {table}.{column} ({sql_type})')
                added += 1

        db.session.commit()

        print('=' * 55)
        if added:
            print(f'[SUCCESS] Migration complete - {added} column(s) added.')
        else:
            print('[SUCCESS] Database already up to date.')
        print('=' * 55)


if __name__ == '__main__':
    migrate()

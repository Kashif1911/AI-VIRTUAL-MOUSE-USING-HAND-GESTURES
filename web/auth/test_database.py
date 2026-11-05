from database import initialize_database, get_connection


print("Initializing authentication database...")

initialize_database()

print("Database initialized successfully.")


connection = get_connection()

try:
    table = connection.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'users'
    """).fetchone()

    if table:
        print("SUCCESS: users table exists.")
    else:
        print("ERROR: users table was not created.")

finally:
    connection.close()

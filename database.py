import sqlite3

def check_database_tables(db_file):
    # Connect to the database
    connection = sqlite3.connect(db_file)
    cursor = connection.cursor()

    # Query to retrieve all table names
    get_tables_query = "SELECT name FROM sqlite_master WHERE type='table';"

    try:
        cursor.execute(get_tables_query)
        tables = cursor.fetchall()

        # Check if there are no tables
        if not tables:
            print("No tables found in the database.")
            return

        # Iterate over the tables and fetch their contents
        for table in tables:
            table_name = table[0]
            print(f"\nContents of table: {table_name}")

            # Query to retrieve data from the current table
            select_query = f"SELECT * FROM {table_name};"
            cursor.execute(select_query)
            rows = cursor.fetchall()

            # Check if the current table is empty
            if not rows:
                print("No data found in this table.")
            else:
                # Display the results
                for row in rows:
                    print(row)

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the connection
        cursor.close()
        connection.close()

# Call the function with your database file
check_database_tables('habit_tracker.db')

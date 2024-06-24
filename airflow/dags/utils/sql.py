import logging 

def convert_to_sql_data_type(val_type):
    if issubclass(val_type, bool):
        return "BOOLEAN"
    elif issubclass(val_type, int):
        return "INTEGER"
    elif issubclass(val_type, float):
        return "FLOAT"
    else:
        return "VARCHAR(255)"

def get_existing_columns(cursor, table_name):
    query = f"""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = '{table_name}';
    """
    cursor.execute(query)
    columns = cursor.fetchall()
    # example return: [('login',), ('id',)]
    return [column[0] for column in columns]

def add_new_columns(cursor, table_name, new_columns):
    for column, data_type in new_columns.items():
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {data_type}")
            logging.info(f"Added new column '{column}' with type '{data_type}' to table '{table_name}'.")
        except Exception as e:
            logging.error(f"Error adding column '{column}': {e}")

def create_or_update_table(connection, data: list[dict], table_name: str):
    cursor = connection.cursor()
    if not data or len(data) == 0:
        logging.warning("data is empty. No table created or updated.")
        return

    # Create table if it doesn't exist
    column_definitions = ", ".join(
        [f"{column} {convert_to_sql_data_type(type(value))}" for column, value in data[0].items()]
    )
    create_table_query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions});"
    try:
        cursor.execute(create_table_query)
        logging.info(f"Table '{table_name}' created or already exists.")
    except Exception as e:
        logging.error(f"Error creating table '{table_name}': {e}")
        return
    connection.commit()

    # Check for new columns and add them
    existing_columns = get_existing_columns(cursor, table_name)
    new_columns = {
        column: convert_to_sql_data_type(value)
        for column, value in data[0].items()
        if column not in existing_columns
    }

    if new_columns:
        add_new_columns(cursor, table_name, new_columns)
        connection.commit()
    else:
        logging.info("No new columns to add.")


def insert_data(connection, data: list[dict], table_name):
    cursor = connection.cursor()

    for element in data:
        columns = element.keys()
        values = [element[column] for column in columns]
        placeholders = ', '.join(['%s'] * len(values))  # Using %s as placeholder for psycopg2
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        cursor.execute(insert_query, values)
        connection.commit()

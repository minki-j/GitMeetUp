def convert_to_sql_data_type(type):
    if issubclass(type, bool):
        return "BOOLEAN"
    elif issubclass(type, int):
        return "INTEGER"
    elif issubclass(type, float):
        return "FLOAT"
    else:
        return "VARCHAR(255)"

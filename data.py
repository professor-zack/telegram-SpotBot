import sqlite3
import os

def create_connection(db_path):
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        sql_create_table_query = """
        CREATE TABLE IF NOT EXISTS spot_stats (
            username TEXT PRIMARY KEY,
            spot_num INTEGER,
            caught_num INTEGER
        );
        """
        cursor = conn.cursor()
        cursor.execute(sql_create_table_query)
    except sqlite3.Error as e:
        print(e) #log error
    return conn

def check_user_in_table(cursor, username):
    sql_query = "SELECT COUNT(*) FROM spot_stats WHERE username = ?"
    cursor.execute(sql_query, (username,))
    result = cursor.fetchone()
    return result[0]>0

def insert_new_user(conn, cursor, username):
    sql_query = "INSERT INTO spot_stats (username, spot_num, caught_num) VALUES (?, 0, 0)"
    cursor.execute(sql_query, (username,))
    conn.commit()
    return

def update_spot_num(conn, spotter, increment_amount):
    cursor = conn.cursor()
    user_in_table = check_user_in_table(cursor, spotter)
    if not user_in_table:
        insert_new_user(conn, cursor, spotter)
    sql_query = "UPDATE spot_stats SET spot_num = spot_num + ? WHERE username = ?"
    cursor.execute(sql_query, (increment_amount, spotter))
    conn.commit()
    return

def update_caught_num(conn, caught_user):
    cursor = conn.cursor()
    user_in_table = check_user_in_table(cursor, caught_user)
    if not user_in_table:
        insert_new_user(conn, cursor, caught_user)
    sql_query = "UPDATE spot_stats SET caught_num = caught_num + 1 WHERE username = ?"
    cursor.execute(sql_query, (caught_user,))
    conn.commit()
    return

def fetch_spotboard(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    sql_query = "SELECT username, spot_num FROM spot_stats ORDER BY spot_num DESC"
    cursor.execute(sql_query)
    results = cursor.fetchall()
    conn.close()
    result_string = results_string_formatter(results)
    return result_string

def fetch_caughtboard(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    sql_query = "SELECT username, caught_num FROM spot_stats ORDER BY caught_num DESC"
    cursor.execute(sql_query)
    results = cursor.fetchall()
    conn.close()
    result_string = results_string_formatter(results)
    return result_string

def results_string_formatter(results):
    output_string = ''
    for idx, result in enumerate(results):
        rank = idx+1
        row = f"{rank}) {result[0]} - {result[1]}\n"
        output_string+=row
    return output_string

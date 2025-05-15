import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os
import json
from datetime import datetime

DB_PATH = r"C:\Projects\OpenWebUI\webui.db"

def connect_to_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        print("Connected to database successfully.")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def get_table_columns(conn, table_name):
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name});")
        return [row[1] for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching columns for {table_name}: {e}")
        return []

def fetch_feedback_data(conn):
    feedback_cols = get_table_columns(conn, 'feedback')
    chat_cols = get_table_columns(conn, 'chat')
    user_cols = get_table_columns(conn, 'user')

    print(f"Feedback table columns: {feedback_cols}")
    print(f"Chat table columns: {chat_cols}")
    print(f"User table columns: {user_cols}")

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM feedback WHERE data IS NOT NULL")
    feedback_count = cursor.fetchone()[0]
    print(f"Feedback table rows with non-null data: {feedback_count}")

    select_cols = [
        "f.id AS feedback_id",
        "f.user_id AS user_id",
        "f.data AS feedback_data",
        "f.created_at AS timestamp",
        "u.name AS user_name",
        "u.email AS user_email",
        "u.role AS user_role"
    ]

    query = f"""
    SELECT {', '.join(select_cols)}
    FROM feedback f
    LEFT JOIN chat c ON f.id = c.id
    LEFT JOIN user u ON f.user_id = u.id
    WHERE f.data IS NOT NULL
    LIMIT 1000;
    """

    try:
        print("Executing query:", query)
        df = pd.read_sql_query(query, conn)
        print("Feedback data fetched successfully.")

        if not df.empty and 'feedback_data' in df.columns:
            df['feedback_data'] = df['feedback_data'].apply(lambda x: json.loads(x) if x else {})
            df['rating'] = df['feedback_data'].apply(lambda x: float(x.get('rating')) if isinstance(x, dict) and x.get('rating') is not None else None)
            df['comment'] = df['feedback_data'].apply(lambda x: x.get('comment') or x.get('text') or x.get('message') if isinstance(x, dict) else None)
            df['model_id'] = df['feedback_data'].apply(lambda x: x.get('model_id') if isinstance(x, dict) else None)
            df['reason'] = df['feedback_data'].apply(lambda x: x.get('reason') if isinstance(x, dict) else None)
            df['sibling_model_ids'] = df['feedback_data'].apply(lambda x: ', '.join(x.get('sibling_model_ids', [])) if isinstance(x, dict) and x.get('sibling_model_ids') else None)
            df['details_rating'] = df['feedback_data'].apply(lambda x: float(x.get('details', {}).get('rating')) if isinstance(x, dict) and isinstance(x.get('details'), dict) and x.get('details').get('rating') is not None else None)

        if 'timestamp' in df.columns:
            df['timestamp'] = df['timestamp'].apply(lambda x: datetime.fromtimestamp(x).strftime('%Y-%m-%d %H:%M:%S') if x else None)

        # Drop feedback_data column as it's now fully parsed
        if 'feedback_data' in df.columns:
            df = df.drop(columns=['feedback_data'])

        print("First 5 rows of data:\n", df.head())
        return df
    except sqlite3.Error as e:
        print(f"Error fetching data: {e}")
        return None

def analyze_feedback(df):
    if df is None or df.empty:
        print("No feedback data to analyze.")
        return

    print("\nFeedback Summary:")
    print(f"Total feedback entries: {len(df)}")
    if 'model_id' in df.columns:
        print(f"Unique models: {df['model_id'].nunique()}")
    if 'rating' in df.columns:
        print(f"Average rating: {df['rating'].mean():.2f}")
    if 'user_id' in df.columns:
        print(f"Unique users: {df['user_id'].nunique()}")

    if 'model_id' in df.columns:
        print("\nFeedback by Model:")
        model_summary = df.groupby('model_id').agg({
            'rating': ['count', 'mean'],
            'comment': 'count',
            'user_id': 'nunique'
        }).round(2)
        model_summary.columns = ['rating_count', 'rating_mean', 'comment_count', 'user_count']
        print(model_summary)

    if 'user_id' in df.columns:
        print("\nFeedback by User:")
        user_summary = df.groupby(['user_id', 'user_name', 'user_email']).agg({
            'rating': ['count', 'mean'],
            'comment': 'count'
        }).round(2)
        user_summary.columns = ['rating_count', 'rating_mean', 'comment_count']
        print(user_summary)

    output_path = "feedback_analysis.csv"
    df.to_csv(output_path, index=False)
    print(f"\nData exported to {output_path}")

    if 'rating' in df.columns and df['rating'].notnull().any():
        plt.figure(figsize=(8, 6))
        df['rating'].hist(bins=[-1.0, -0.9, -0.8, -0.7, -0.6, -0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], edgecolor='black')
        plt.title('Detailed Distribution of Feedback Ratings')
        plt.xlabel('Rating')
        plt.ylabel('Count')
        plt.xticks([-1.0, -0.5, 0.0, 0.5, 1.0])
        plt.grid(True, alpha=0.3)
        plt.savefig('rating_distribution.png')
        print("Rating distribution plot saved as 'rating_distribution.png'")

def main():
    conn = connect_to_db(DB_PATH)
    if not conn:
        return

    df = fetch_feedback_data(conn)
    if df is not None:
        analyze_feedback(df)

    conn.close()
    print("Database connection closed.")

if __name__ == "__main__":
    main()
import mysql.connector

def fix_database():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  # अपना पासवर्ड डालें अगर है तो
            database="skillnexa_db" # अपने डेटाबेस का नाम लिखें
        )
        cursor = conn.cursor()
        
        # viewer_ip कॉलम ऐड करने की कोशिश
        try:
            cursor.execute("ALTER TABLE profile_views ADD COLUMN viewer_ip VARCHAR(50) AFTER employer_id")
            print("Success: 'viewer_ip' column added successfully!")
        except mysql.connector.Error as err:
            if err.errno == 1060: # Column already exists
                print("Info: Column 'viewer_ip' already exists.")
            else:
                print(f"Error: {err}")
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    fix_database()
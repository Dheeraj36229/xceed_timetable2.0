from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import os
import threading
from datetime import datetime

# Import your existing scraper and background worker logic
from processtimetable import process_timetables
from botworker import reminderstart, start_keep_alive

app = Flask(__name__)
CORS(app)

FILE_NAME = "user_settings.txt"

def load_data():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_data(data):
    with open(FILE_NAME, "w") as f:
        json.dump(data, f, indent=4)

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import json
# Import your scraper function
from processtimetable import process_timetables

app = Flask(__name__)
CORS(app)

FILE_NAME = "user_settings.txt"

@app.route('/process-all', methods=['POST'])
def process_all():
    new_data = request.json
    username = new_data.get('instagram', 'user')

    # 1. Save data to file so process_timetables can read it
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data[username] = {
        "session": new_data.get('session'),
        "department": new_data.get('department'),
        "section": new_data.get('section'),
        "status": "pending"
    }

    with open(FILE_NAME, "w") as f:
        json.dump(data, f, indent=4)

    # 2. Generate the PDF
    try:
        # 1. Generate the PDF via your scraper
        success = process_timetables()
        pdf_path = f"{username}_tb.pdf"

        if success and os.path.exists(pdf_path):
            # 2. Create a function to send and then delete
            def generate_and_cleanup():
                with open(pdf_path, 'rb') as f:
                    yield from f
                # Delete the file immediately after streaming is done
                try:
                    os.remove(pdf_path)
                    print(f"Successfully deleted temporary file: {pdf_path}")
                except Exception as e:
                    print(f"Error deleting file: {e}")

            # 3. Return the file as a stream
            return app.response_class(
                generate_and_cleanup(),
                mimetype='application/pdf',
                headers={"Content-Disposition": f"attachment; filename=Timetable_{username}.pdf"}
            )
        else:
            return jsonify({"status": "error", "message": "PDF failed"}), 500
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

reminder_started = False
@app.route('/set-reminder', methods=['POST'])
def set_reminder():
    """Saves the browser push subscription and starts the notification thread."""
    global reminder_started
    new_data = request.json
    username = new_data.get('instagram')
    subscription = new_data.get('subscription') # The JSON object from browser PushManager
    
    if not username or not subscription:
        return jsonify({"status": "error", "message": "Missing username or subscription data"}), 400

    data_dict = load_data()

    # Save the browser subscription token instead of Instagram info
    data_dict[username] = {
        "session": new_data.get('session'),
        "department": new_data.get('department'),
        "section": new_data.get('section'),
        "subscription": subscription,
        "reminder_status": "yes",
        "status": "completed"
    }

    save_data(data_dict)

    # Start the background reminder thread if not already running
    boot_system()
   
    return jsonify({"status": "success", "message": "Reminder set!"})

def boot_system():
    global reminder_started
    if not reminder_started:
        t = threading.Thread(target=reminderstart, daemon=True)
        t.start()
        reminder_started=True
        print("Server Booted. Background services initializing...")
from flask import send_from_directory

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.getcwd(), 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory(os.getcwd(), 'sw.js')
from flask import send_from_directory

@app.route('/static/<path:path>')
def serve_static(path):
    # This serves your logos, icons, and banners to the browser
    return send_from_directory('static', path)
@app.route('/test-push/<username>')
def test_push(username):
    if not os.path.exists(FILE_NAME):
        return "No users found"

    with open(FILE_NAME, "r") as f:
        data = json.load(f)

    if username in data and "subscription" in data[username]:
        settings = data[username]
        # This calls your existing push function from botworker.py
        from botworker import send_web_push 
        
        test_message = {
            "title": "🚀 XCEED | Test Alert",
            "body": "Your branding is working! Next class: Demo Lab"
        }
        
        success = send_web_push(settings["subscription"], json.dumps(test_message))
        return f"Push sent! Status: {success}"
    
    return "User or subscription not found. Make sure you clicked 'Set Reminder' first."

# Automatic boot trigger

if __name__ == '__main__':
    # Update with your actual Render URL
    boot_system()

    start_keep_alive("https://your-timetable-bot.onrender.com") 
    app.run(port=5000, debug=True)

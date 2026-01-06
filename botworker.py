import os
import json
import time
import threading
import requests
from datetime import datetime
from pywebpush import webpush, WebPushException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from processtimetable import get_driver, run_timetable_selection

# --- CONFIGURATION ---
# Generate these using: pywebpush --generate-vapid-keys
VAPID_PRIVATE_KEY = "Vm13EIml5__S0I5UVvICG-RFWDiFqSoDUEpfC40G1no"
VAPID_CLAIMS = {
    "sub": "mailto:your-email@example.com"
}

FILE_NAME = "user_settings.txt"

# [cite_start]Time slots based on the PDF structure (8:30, 9:30, etc.) [cite: 1]
class_slots = [
    (8, 30), (9, 30), (10, 30), (11, 30), 
    (13, 30), (14, 30), (15, 30), (16, 30)
]

def send_web_push(subscription_info, message_body):
    """Sends a notification to the browser using the stored subscription token."""
    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps({
                "title": "🚀 XCEED | Next Class",
                "body": message_body
            }),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
        print(f"Push notification sent successfully.")
    except WebPushException as ex:
        print(f"Web Push Error: {ex}")
        # If the browser has revoked permission, you might want to remove the user
        if ex.response and ex.response.status_code == 410:
            print("Subscription expired or removed by user.")

def reminderstart():
    """Background service that checks the time and sends alerts."""
    print("Web Push Reminder service started...")
    
    while True:
        now = datetime.now()
        weekday = now.weekday() # 0=Monday, 4=Friday [cite: 1]
        
        # Weekend check (Saturday=5, Sunday=6)
        if weekday > 4:
            time.sleep(3600) # Sleep for an hour
            continue

        for idx, slot in enumerate(class_slots):
            # [cite_start]Trigger 5 minutes before the class starts [cite: 1]
            if now.hour == slot[0] and now.minute == (slot[1] - 5):
                
                if not os.path.exists(FILE_NAME):
                    continue

                with open(FILE_NAME, "r") as f:
                    try:
                        data = json.load(f)
                    except:
                        continue

                for username, settings in data.items():
                    # Only process users with 'yes' status and a valid browser subscription
                    if settings.get("reminder_status") == "yes" and "subscription" in settings:
                        process_single_reminder(username, settings, weekday, idx, slot)
                
                # Prevent multiple triggers within the same minute
                time.sleep(60)
        
        time.sleep(30) # Check every 30 seconds

def process_single_reminder(username, settings, weekday, slot_idx, slot_time):
    """Uses Selenium to find the class name and sends the push notification."""
    driver = None
    try:
        print(f"Finding class for {username} at {slot_time[0]}:{slot_time[1]}...")
        driver = get_driver()
        wait = WebDriverWait(driver, 30)
        
        run_timetable_selection(driver, wait, settings)
        
        # [cite_start]Correct XPATH calculation for the timetable grid [cite: 1]
        # weekday + 1 for row, slot_idx + 2 for column (skipping the 'Day' column)
        xpath = f"/html/body/div[1]/div/div[4]/div[2]/div[2]/div/div[1]/div/div/table/tbody/tr[{weekday+1}]/td[{slot_idx+2}]/div"
        
        class_element = driver.find_element(By.XPATH, xpath)
        class_info = class_element.text.strip()
        
        if class_info and class_info != "":
            msg = f"Upcoming class: {class_info} at {slot_time[0]}:{slot_time[1]}"
            send_web_push(settings['subscription'], msg)
        else:
            print(f"No class scheduled for {username} in this slot.")

    except Exception as e:
        print(f"Reminder Error for {username}: {e}")
    finally:
        if driver:
            driver.quit()

def keep_alive(url):
    """Pings the server to prevent sleep (useful for Render/Heroku)."""
    while True:
        try:
            requests.get(url)
            print("Keep-alive ping sent.")
        except Exception as e:
            print(f"Ping failed: {e}")
        time.sleep(600) # 10 minutes

def start_keep_alive(url):
    t = threading.Thread(target=keep_alive, args=(url,), daemon=True)
    t.start()
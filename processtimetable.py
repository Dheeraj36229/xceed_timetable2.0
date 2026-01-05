import os
import time
import base64
import json
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

FILE_NAME = "user_settings.txt"

def get_driver():
    """Configures a headless Chrome driver for automated scraping."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Using a real user agent to prevent being blocked by the portal
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def safe_select(wait, xpath, text, retries=5):
    """Safely selects an option from a dropdown with retries."""
    for i in range(retries):
        try:
            element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            dropdown = Select(element)
            # Normalize text to match options exactly
            if text in [o.text.strip() for o in dropdown.options]:
                dropdown.select_by_visible_text(text)
                time.sleep(2) # Wait for dependent dropdowns to load
                return True
        except Exception as e:
            pass
        time.sleep(2)
    raise Exception(f"Failed to find option '{text}' in dropdown {xpath}")

def run_timetable_selection(driver, wait, settings):
    """Navigates the NITJ portal and selects the specific timetable."""
    driver.get("https://xceed.nitj.ac.in/timetable")
    
    # Select Session
    safe_select(wait, "//select[contains(@class, 'chakra-select')]", settings["session"])
    
    # Select Department
    safe_select(wait, "//*[@id='root']/div/div[3]/select", settings["department"])
    
    # Select Section/Semester
    safe_select(wait, "/html/body/div[1]/div/div[4]/div[2]/div[1]/select", settings["section"])

def process_timetables():
    """Main logic to generate the PDF for users marked as 'pending'."""
    if not os.path.exists(FILE_NAME):
        return False

    with open(FILE_NAME, "r") as f:
        data = json.load(f)

    success_flag = False

    for username, settings in data.items():
        if settings.get("status") == "pending":
            print(f"Generating PDF for: {username}")
            driver = get_driver()
            wait = WebDriverWait(driver, 30)
            
            try:
                run_timetable_selection(driver, wait, settings)
                
                # Locate and click the 'View/Print' button
                btn_xpath = "/html/body/div[1]/div/div[4]/div[2]/div[2]/div/div[2]/div[2]/button"
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
                driver.execute_script("arguments[0].click();", btn)
                
                # Wait for the new tab with the PDF to open
                wait.until(lambda d: len(d.window_handles) > 1)
                driver.switch_to.window(driver.window_handles[1])
                
                # JavaScript to fetch the PDF as a Base64 string from the browser blob
                js_script = """
                var callback = arguments[arguments.length - 1];
                fetch(window.location.href)
                    .then(response => response.blob())
                    .then(blob => {
                        var reader = new FileReader();
                        reader.onloadend = function() {
                            callback(reader.result);
                        };
                        reader.readAsDataURL(blob);
                    });
                """
                base64_data = driver.execute_async_script(js_script)
                
                if "base64," in base64_data:
                    # Decode and save the PDF locally
                    pdf_content = base64.b64decode(base64_data.split("base64,")[1])
                    with open(f"{username}_tb.pdf", "wb") as f_pdf:
                        f_pdf.write(pdf_content)
                    
                    settings["status"] = "completed"
                    success_flag = True
                    print(f"Successfully generated {username}_tb.pdf")
                
            except Exception as e:
                print(f"Error generating PDF for {username}: {e}")
            finally:
                driver.quit()

    # Save the updated status back to the settings file
    with open(FILE_NAME, "w") as f:
        json.dump(data, f, indent=4)
    
    return success_flag

if __name__ == "__main__":
    # Manual trigger for testing
    process_timetables()
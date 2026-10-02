import pyautogui
from datetime import datetime
import time
import pyscreeze
import pyperclip
import re
#import openpyxl # creating/saving the Excel

file_date = datetime.now().strftime("%Y-%m-%d")
filename = f"daily_report_{file_date}.xlsx"

# Open the website
pyautogui.hotkey("win", "r")
pyautogui.write("chrome")
time.sleep(1)
pyautogui.press("enter")
time.sleep(1)

pyautogui.hotkey("ctrl", "t")  # Press Ctrl+T to open a new tab
pyautogui.typewrite("https://www.xe.com/currencyconverter/", interval=0.1)  # Type the URL with a 0.1 second interval between keys
pyautogui.press("enter")  # Press Enter to navigate to the URL
time.sleep(3)

pyautogui.scroll(-500)  # Scroll down 500 units
time.sleep(3)

# Scrap data
pyautogui.moveTo(250,500, duration=1)  # Move the mouse to the specified coordinates (x=250, y=590) over 1 second
pyautogui.dragTo(750, 500, duration=1, button="left")  # Drag the mouse to the specified coordinates (x=730, y=590) over 1 second
time.sleep(0.5)
pyautogui.hotkey("ctrl", "c")

# Read the copied text from the clipboard
rate_text = pyperclip.paste()
print("Copied:", rate_text)

# Extract rate
match = re.search(r'=\s*([0-9]+(?:\.[0-9]+)?)', rate_text)
if match:
    rate = float(match.group(1))
    print("Exchange rate:", rate)

    # screenshot
    pyautogui.screenshot(f"{file_date}.png")
else:
    print("Exchange rate not found")

pyautogui.hotkey("alt", "f4") # Press Alt+F4 to close the current window

# Open excel
pyautogui.hotkey("win", "r")  # Press Win+R to open the Run dialog
pyautogui.write("excel")  # Type "excel" in the Run dialog
pyautogui.press("enter")  # Press Enter to launch Excel
time.sleep(5)

# create a new workbook
pyautogui.hotkey("ctrl", "n")
time.sleep(2)

# Write headers to the Excel file
pyautogui.write("Date & Time")
pyautogui.press("tab")

pyautogui.write("USD to EUR")
pyautogui.press("tab")

pyautogui.write("Remarks")
pyautogui.press("enter")
time.sleep(2)

# Write the data to the Excel file
now = datetime.now()
date_time = now.strftime("%Y-%m-%d %H:%M:%S")
pyautogui.write(date_time)
pyautogui.press("tab")

pyautogui.write(str(rate))
pyautogui.press("tab")
pyautogui.write("Exchange rate fetched successfully")
time.sleep(2)

pyautogui.hotkey("ctrl", "s")
pyautogui.write(filename)
pyautogui.press("enter")








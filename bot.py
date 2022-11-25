from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import re
import os.path
from os import path
import sqlite3
import schedule
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains
import discord_webhook
import pyautogui

opt = Options()
opt.add_argument("--disable-infobars")
opt.add_argument("start-maximized")
opt.add_argument("--disable-extensions")
opt.add_argument("--start-maximized")
# Pass the argument 1 to allow and 2 to block, need to allow by default for teams in order to join a channel
opt.add_experimental_option("prefs", { \
    "profile.default_content_setting_values.media_stream_mic": 1, 
    "profile.default_content_setting_values.media_stream_camera": 1,
    "profile.default_content_setting_values.geolocation": 1, 
    "profile.default_content_setting_values.notifications": 1 
  })

# driver = webdriver.Chrome(chrome_options=opt, service_log_path='NUL')
driver = None
URL = "https://teams.microsoft.com"

# Put your teams credentials here
CREDS = {'email':'', 'passwd':''}


def login():
	global driver
	#login required
	print("Logging in")
	emailField = driver.find_element_by_xpath('//*[@id="i0116"]')
	emailField.click()
	emailField.send_keys(CREDS['email'])
	driver.find_element_by_xpath('//*[@id="idSIButton9"]').click() #Next button
	time.sleep(5)
	passwordField = driver.find_element_by_xpath('//*[@id="i0118"]')
	passwordField.click()
	passwordField.send_keys(CREDS['passwd'])
	driver.find_element_by_xpath('//*[@id="idSIButton9"]').click() #Sign in button
	time.sleep(5)
	driver.find_element_by_xpath('//*[@id="idSIButton9"]').click() #remember login
	time.sleep(5)
	# return driver


def createDB():
	conn = sqlite3.connect('timetable.db')
	c=conn.cursor()
	# Create table
	c.execute('''CREATE TABLE timetable(class text, channel text, start_time text, end_time text, day text)''')
	conn.commit()
	conn.close()
	print("Created timetable db")


def validate_input(regex, inp):
	if not re.match(regex, inp):
		return False
	return True

def validate_day(inp):
	days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

	if inp.lower() in days:
		return True
	else:
		return False


def add_timetable():
	if(not(path.exists("timetable.db"))):
		createDB()
	op = int(input("1. Add class\n2. Done adding\nEnter option: "))
	while(op==1):
		name = input("Enter class name: ")
		while name.isspace() or len(name)==0:
			print("Invalid input, try again")
			name = input("Enter class name: ")

		channel = input("Enter channel name (defaults to General): ")
		if channel.isspace() or len(channel)==0:
			channel = "General"

		start_time = input("Enter class start time in 24 hour format (HH:MM): ")
		while not(validate_input("\d\d:\d\d", start_time)):
			print("Invalid input, try again")
			start_time = input("Enter class start time in 24 hour format (HH:MM): ")

		end_time = input("Enter class end time in 24 hour format (HH:MM): ")
		while not(validate_input("\d\d:\d\d", end_time)):
			print("Invalid input, try again")
			end_time = input("Enter class end time in 24 hour format (HH:MM): ")

		day = input("Enter day (Monday/Tuesday/Wednesday..etc): ")
		while not(validate_day(day.strip())):
			print("Invalid input, try again")
			end_time = input("Enter day (Monday/Tuesday/Wednesday..): ")

		conn = sqlite3.connect('timetable.db')
		c = conn.cursor()

		# Insert a row of data
		c.execute("INSERT INTO timetable VALUES ('%s','%s','%s','%s','%s')"%(name, channel, start_time, end_time, day))

		conn.commit()
		conn.close()

		print("Class added to database\n")

		op = int(input("1. Add class\n2. Done adding\nEnter option : "))


def view_timetable():
	conn = sqlite3.connect('timetable.db')
	c = conn.cursor()
	for row in c.execute('SELECT * FROM timetable'):
		print(row)
	conn.close()


def joinclass(class_name, channel_name = "General", start_time = 0, end_time = 0):
	global driver

	try_time = int(start_time.split(":")[1]) + 15
	try_time = start_time.split(":")[0] + ":" + str(try_time)

	time.sleep(5)



	#for i in classes_available:
	#	if class_name.lower() in i.get_attribute('innerHTML').lower():
	#		print("JOINING CLASS ", class_name)
	#		i.click()
	#		break
    #

	#for j in channels_available:
	#	if channel_name.lower() in j.get_attribute('innerHTML').lower():
	#		print("IN CHANNEL ", channel_name)
	#		j.click()
	#		break


	xpath_class_name = "//*[@data-tid='team-" + class_name + "']"

	#xpath_channel_name = xpath_class_name + "/div/ul/ng-include//*[@data-tid='team-" + class_name + "-channel-" + channel_name + "']"
	xpath_channel_name = "//*[@data-tid='team-" + class_name + "-channel-" + channel_name + "']"

	# Check if the needed classroom is already expanded in the list view, else click to expand it (expanded list elements have a div after the h3 title)
	if len(driver.find_elements_by_xpath(xpath_class_name + "/div")) == 0:
		for i in classes_available:
			if class_name.lower() in i.get_attribute('innerHTML').lower():
				i.click()
				break

	#channels_available = driver.find_elements_by_class_name("channels")

	# Click to select the needed channel of the classroom
	if len(driver.find_elements_by_xpath(xpath_channel_name)) != 0:
		driver.find_element_by_xpath(xpath_channel_name).click()
		print("JOINING CLASS ", class_name, "CHANNEL ", channel_name)
	else:
		print("NOT FOUND ", channel_name, ":", class_name)

	time.sleep(4)

	try:
		joinbtn = driver.find_element_by_class_name("ts-calling-join-button")
		joinbtn.click()

	except:
		#join button not found (maybe class hasn't started yet)
		#refresh every minute
		k = 1
		while(k<=15):
			print("Join button not found, trying again")
			time.sleep(60)
			driver.refresh()
			joinclass(class_name, channel_name, start_time, end_time)
			#schedule.every(1).minutes.do(joinclass,class_name,start_time,end_time)
			k+=1
		print("Seems like there is no class today")
		discord_webhook.send_msg(class_name=class_name, channel_name=channel_name, status="noclass", start_time=start_time, end_time=end_time)


	time.sleep(4)
	webcam = driver.find_element_by_xpath('//*[@id="page-content-wrapper"]/div[1]/div/calling-pre-join-screen/div/div/div[2]/div[1]/div[2]/div/div/section/div[2]/toggle-button[1]/div/button/span[1]')
	if(webcam.get_attribute('title')=='Turn camera off'):
		webcam.click()
	time.sleep(1)

	microphone = driver.find_element_by_xpath('//*[@id="preJoinAudioButton"]/div/button/span[1]')
	if(microphone.get_attribute('title')=='Mute microphone'):
		microphone.click()

	time.sleep(1)
	joinnowbtn = driver.find_element_by_xpath('//*[@id="page-content-wrapper"]/div[1]/div/calling-pre-join-screen/div/div/div[2]/div[1]/div[2]/div/div/section/div[1]/div/div/button')
	joinnowbtn.click()

	discord_webhook.send_msg(class_name=class_name, channel_name=channel_name, status="joined", start_time=start_time, end_time=end_time)
	
	#Now schedule leaving class
	tmp = "%H:%M"

	class_running_time = datetime.strptime(end_time,tmp) - datetime.strptime(start_time,tmp)

	time.sleep(class_running_time.seconds)

	driver.find_element_by_class_name("ts-calling-screen").click()


	driver.find_element_by_xpath('//*[@id="teams-app-bar"]/ul/li[3]').click() #come back to homepage
	time.sleep(1)

	driver.find_element_by_xpath('//*[@id="hangup-button"]').click()
	print("Class left")
	discord_webhook.send_msg(class_name=class_name, channel_name=channel_name, status="left", start_time=start_time, end_time=end_time)



def start_browser():

	global driver
	driver = webdriver.Chrome(chrome_options=opt, service_log_path='NUL')

	driver.get(URL)

	WebDriverWait(driver, 10000).until(EC.visibility_of_element_located((By.TAG_NAME, 'body')))

	if("login.microsoftonline.com" in driver.current_url):
		login()


def sched():
	conn = sqlite3.connect('timetable.db')
	c=conn.cursor()
	for row in c.execute('SELECT * FROM timetable'):
		#schedule all classes
		name = row[0]
		channel = row[1]
		start_time = row[2]
		end_time = row[3]
		day = row[4]

		#TODO I was lazy, should refactor and implement a dictionary
		if day.lower()=="monday":
			schedule.every().monday.at(start_time).do(joinclass, name, channel, start_time, end_time)
			print("Scheduled class '%s', channel '%s' on %s at %s"%(name, channel, day, start_time))
		if day.lower()=="tuesday":
			schedule.every().tuesday.at(start_time).do(joinclass, name, channel, start_time, end_time)
			print("Scheduled class '%s', channel '%s' on %s at %s"%(name, channel, day, start_time))
		if day.lower()=="wednesday":
			schedule.every().wednesday.at(start_time).do(joinclass, name, channel, start_time, end_time)
			print("Scheduled class '%s', channel '%s' on %s at %s"%(name, channel, day, start_time))
		if day.lower()=="thursday":
			schedule.every().thursday.at(start_time).do(joinclass, name, channel, start_time, end_time)
			print("Scheduled class '%s', channel '%s' on %s at %s"%(name, channel, day, start_time))
		if day.lower()=="friday":
			schedule.every().friday.at(start_time).do(joinclass, name, channel, start_time, end_time)
			print("Scheduled class '%s', channel '%s' on %s at %s"%(name, channel, day, start_time))
		if day.lower()=="saturday":
			schedule.every().saturday.at(start_time).do(joinclass, name, channel, start_time, end_time)
			print("Scheduled class '%s', channel '%s' on %s at %s"%(name, channel, day, start_time))
		if day.lower()=="sunday":
			schedule.every().sunday.at(start_time).do(joinclass, name, channel, start_time, end_time)
			print("Scheduled class '%s', channel '%s' on %s at %s"%(name, channel, day, start_time))

		#TODO Check conflicting schedules and throw a warning, intersecting timeliness not supported at this time (can be done by worker threads in the future)


	#Start browser
	start_browser()
	while True:
		# Checks whether a scheduled task
		# is pending to run or not
		schedule.run_pending()
		time.sleep(1)


if __name__=="__main__":
	# joinclass("Maths","15:13","15:15","sunday")
	op = int(input(("1. Modify Timetable\n2. View Timetable\n3. Start Bot\nEnter option : ")))
	
	if(op==1):
		add_timetable()
	if(op==2):
		view_timetable()
	if(op==3):
		sched()
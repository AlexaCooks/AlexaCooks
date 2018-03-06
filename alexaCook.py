#!/usr/bin/python
from flask import Flask
from flask_ask import Ask, statement, question, session

import json
import requests
import time
import unidecode
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import mysql.connector 

db =  mysql.connector.connect(host="localhost",    # your host, usually localhost
                     user="root",         # your username
                     passwd="12345678",  # your password
                     db="userDb")        # name of the data base


####GLOBALS#### Should probably make this a class if we got time...
ingredients = []
steps = []
currentTitle = ""
currentStep = 0
recipeOptions = []
currentRecipe = 0
currentDoc = ""
#Flask App stuff
app = Flask(__name__)
ask = Ask(app, "/alexa_cooks")

#Returns wheter or not the table is empty 
def dbEmpty():
	cur = db.cursor()
	cur.execute("SELECT * FROM user")
	result = cur.fetchall()
	print(result)
	return len(result) == 0

#Updates db, Inserts if empty, Updates if there is data
def updateDb():
	cur = db.cursor()
	global currentStep
	global currentRecipe
	global currentTitle
	global currentDoc
	data = (currentStep, currentRecipe, currentTitle)
	if dbEmpty(): #If no data is saved, save into DB
		print("db empty")
		action = "INSERT user VALUES {}".format(data)
		print(action)
	else: #otherwise update sql record of user
		print("db not empty")
		action = "UPDATE user  SET curentStep={}".format(currentStep)
		action += ", curentRecipe={}".format(currentRecipe)
		action += ", recpieName={}".format( '"' + currentTitle + '"')
		action += " WHERE 1=1"
		print(action)
	cur.execute(action)
	db.commit()

def clearDb():
	cur = db.cursor()
	if not dbEmpty():
		cur.execute("DELETE FROM user")
		db.commit()

def loadFromDb():
	cur = db.cursor()
	cur.execute("SELECT * FROM user")
	result = cur.fetchall()[0]
	global currentStep
	global currentRecipe
	global currentTitle
	currentStep = result[0]
	currentRecipe = result[1]


	#use turneary operator here to be cool af
	print(result[2])
	if "|" in result[2]:#remove | Serious eats
		currentTitle = result[2].split("|")[1]
	else:
		currentTitle = result[2]
	print(currentTitle)


#requires that query is a string that returns valid results when searching SeriousEats
#given a query like "apple pie", gets recipie, ingredients
def loadRecipieOptions(query):
	query = query.replace(" ", "+") + "+"
	print(query)
	#adding BraveTart to serious eats will force it to look for only baking recipes
	url = "https://www.seriouseats.com/search?term=" + query + "brave+tart&site=recipes"
	print(url)
	req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
	web_bytes = urlopen(req).read()
	#get raw webpage
	webpage = web_bytes.decode('utf-8')
	#format and parse serch results
	#the string "<div class=..." helps us get to the part of the HTML with the recipe
	soup = BeautifulSoup('<div class="metadata">\n<a class="module__link" '+ webpage.split('a class="module__link"', 1)[1], "html.parser")

	#extract relevent links and titles
	links = soup.find_all('a')
	#remove the "see more" link 
	links.pop()
	titles = soup.find_all('h4')

	#provide 5 recipie options
	global recipeOptions
	recipeOptions = []
	print("recipeOptions")
	print(recipeOptions)
	for recipeID in range(5): #[(title, link), (title, link)...]
		print(titles[recipeID].get_text())
		print(links[recipeID].get('href'))
		recipeOptions.append((titles[recipeID].get_text(), links[recipeID].get('href')))


#given currentDoc is a valid HTML recipie document, format Docuent into steps and ingredients
def  formatRecipie():
	global currentDoc
	soup = BeautifulSoup(currentDoc, "html.parser")
	#get steps and ingredients
	global ingredients
	global steps
	#make ingredients and steps empty if they have stufff
	ingredients = []
	steps = []
	li_tags = soup.find_all('li')
	#loop through relevant HTML tags and get recipe and ingredients
	for tag in li_tags:
		if('class="ingredient" itemprop="ingredients' in str(tag)):
			ingredients.append(tag.get_text())
		if('class="recipe-procedure-text"' in str(tag)):
			step = tag.get_text().split(None, 1)[1].split(". ")
			#break up big steps in to small steps
			for action in step:
				steps.append(action)
	print("guccigangguccigangguccigangguccigangguccigang")
	print(ingredients)

#Loads a recipe document from Serious eats if no previous recipie is stored
#Loads a recipe document from the HTML file if one is previously saved
def loadCurrentRecipe():
	print(recipeOptions)
	print(currentRecipe)
	global currentDoc;
	global currentTitle
	if dbEmpty():#app is starting with fresh recipie
		print("EMPTY")
		url = recipeOptions[currentRecipe][1]
		currentTitle = recipeOptions[currentRecipe][0]
		print(currentTitle)
		req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
		web_bytes = urlopen(req).read()
		currentDoc = web_bytes.decode('utf-8')
		fp = open("doc.html","w")
		fp.write(currentDoc)
	else:  
		print("NOT EMPTY")
		#get recipie data from DB         
		loadFromDb()
		fp = open("doc.html","r")
		currentDoc = fp.read()


#START of our Alexa skill. START with: "Alexa, let's start cooking"
@ask.launch
def startSkill():
	#if no data is saved, we search for a recipie
	if dbEmpty(): 
		greeting =  "Welcom to Alexa Cooks. You can ask me for recipes. For example just say, 'Search for apple pie.' What would you like to bake?"
		#greeting = "db empty"
	#otherwise provide option to return to previously saved recipie
	else:
		greeting = "Welcom to Alexa Cooks. Say next step, or search for a new recipie."
		loadFromDb()
		loadCurrentRecipe()
		formatRecipie()
	return question(greeting)    


#Trigger this function with: "Search for <query> recipes
@ask.intent("SearchRecpieIntent")
def queryRecipies(RecpieQuery):
	if "souffle" in RecpieQuery:
		return statement("Hmm... I don't know. How about a cupcake instead?")
	loadRecipieOptions(RecpieQuery)
	clearDb()
	global currentTitle
	loadCurrentRecipe()
	response = "I found " + currentTitle + ". " + " Would you like to try it?"
	return question(response)

#Yes we are trying this recipie--launch and read first step
@ask.intent("YesIntent")
def launchRecipe():
	print("YES TRIGGERED--launching")
	# username = "your_textmagic_username"
	# token = "your_apiv2_key"
	# client = TextmagicRestClient(username, token)
	# message = client.messages.create(phones="7343836484", text="Hello TextMagic")
	formatRecipie()
	global currentStep
	global steps
	print(steps)
	currentStep = 0
	print(currentStep)
	response = steps[currentStep]
	updateDb()
	return question(response)

#Get a new recipie
@ask.intent("NoIntent")
def pickNewRecipe():
	print("NO TRIGGERED")
	global currentRecipe
	currentRecipe += 1
	loadCurrentRecipe()
	response = "Okay, I found " + currentTitle + ". " + " Would you like to try it?"
	#add a reprompt here if u got time
	return question(response)


#Trigger this function with: "Next step!"
@ask.intent("AMAZON.NextIntent")
def nextStep():
	print("NEXT Triggered")
	global steps
	global currentStep
	currentStep += 1
	updateDb()
	#we have finished the recipe. Clear database, and close the app. 
	if currentStep == len(steps):
		clearDb()
		return statement("You have finished the recipe. Enjoy!")
	#otherwise give next step...
	print(steps)
	print(currentStep)
	step = steps[currentStep]
	return question(step)


#Trigger this function with: "Previous step!"
@ask.intent("AMAZON.PreviousIntent")
def previousStep():
	global steps
	global currentStep
	currentStep -= 1
	step = steps[currentStep]
	updateDb()
	return question(step)

#Trigger this function with: "Repeat step!"
@ask.intent("AMAZON.RepeatIntent")
def repeatStep():
	global steps
	global currentStep
	return question(steps[currentStep])


@app.route('/')
def homepage():
	return "Ayyyyooo"


#Run our application
if __name__ == "__main__":
	app.run(debug=True)














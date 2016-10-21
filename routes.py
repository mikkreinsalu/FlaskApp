# -*- coding: UTF-8 -*-
from flask import Flask,  render_template, request
import psycopg2
import psycopg2.extensions
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

app = Flask(__name__)

def connectDB():

	try:
		return psycopg2.connect(database="firmad", user="miq", host="localhost", port="5432")
	except:
		print("Can't connect to database")

#creating tables
conn = connectDB()
print "Database opened"
cur = conn.cursor()

cur.execute('''SELECT EXISTS(SELECT 1 FROM information_schema.tables 
	WHERE table_catalog='firmad' 
	AND table_schema='public' 
	AND table_name='company');''')

checkTable = cur.fetchone()[0] 

if checkTable is False:
	cur.execute('''CREATE TABLE company
	       (company_id 		SERIAL 		PRIMARY KEY     NOT NULL,
	       name           VARCHAR(100)    NOT NULL,
	       regnr            VARCHAR(7)     NOT NULL,
	       regdate        VARCHAR(30)		NOT NULL,
	       capital			VARCHAR(15)		NOT NULL);''')
	cur.execute('''CREATE TABLE owner
		(owner_id 	SERIAL 		PRIMARY KEY		NOT NULL,
		owner_name 	VARCHAR(100) 	NOT NULL,
		owner_data	VARCHAR(15)	NOT NULL,
		owner_part	VARCHAR(15) NOT NULL,
		company_id	INTEGER REFERENCES company);''')
	print "Tables made"
else:
	print "Tables exist"

conn.commit()
conn.close()

def checkDigit(checkStr):
	if (not checkStr.isnumeric()):
		return False
	return True

def checkLists(checkList):
	for line in checkList:
		if (not line.isdigit()):
			return False
	return True

def checkData(name, regnr, registerDate, cap, ownercaplist):

	newCap = int(cap)
	conn = connectDB()
	cur = conn.cursor()
	total = 0
	for line in ownercaplist:
		total += int(line)
	cur.execute('''SELECT EXISTS(SELECT * FROM company WHERE name = %s OR regnr = %s);''', (name, regnr))
	checkResult = cur.fetchone()[0]
 
	if (not checkResult) and len(str(name)) >= 3 and len(str(regnr)) == 7 and newCap >= 2500 and newCap == total:
		return False
	else:
		return True

	conn.commit()
	conn.close()

@app.route("/")
def home():
	return render_template('home.html')

@app.route("/createAccount")
def createAccount():
	return render_template('createAccount.html')

@app.route("/newCompany", methods=['POST'])
def newAccount():

	#requesting data
	companyName = request.form['name']
	companyReg = request.form['regNumber']
	regDate = request.form['date']
	companyCap = request.form['capital']
	ownerName = request.form['owner']
	ownerData = request.form['ownerData']
	ownerShares = request.form['ownerShares']

	#creating lists for owner table
	ownerNameStr = ownerName.encode('ascii', 'replace')
	ownerSharesStr = ownerShares.encode('ascii', 'replace')
	ownerDataStr = ownerData.encode('ascii', 'replace')
	ownerNameArray = ownerNameStr.split(',')
	ownerSharesArray = ownerSharesStr.split(',')
	ownerDataArray = ownerDataStr.split(',')
	ownerNameList = []
	ownerDataList = []
	ownerSharesList = []

	for line in ownerNameArray:
		line = line.strip()
		line = line.title()
		ownerNameList.append(line)

	for line in ownerDataArray:
		line = line.strip()
		ownerDataList.append(line)
	
	for line in ownerSharesArray:
		line = line.strip()
		ownerSharesList.append(line)

	#checking if data is correct
	if (not checkDigit(companyCap)) or (not checkDigit(companyReg)):
		return render_template('error.html')
	elif (not checkLists(ownerDataList)) or (not checkLists(ownerSharesList)):
		return render_template('error.html')
	elif checkData(companyName, companyReg, regDate, companyCap, ownerSharesList):
		return render_template('error.html')
	else:
		conn = connectDB()
		cur = conn.cursor()
		try:
			cur.execute('''INSERT INTO company (name, regnr, regdate, capital)
				VALUES (%s, %s, %s, %s);''',
				(companyName, companyReg, regDate, companyCap) )
		except:
			print("Error inserting into company")
		conn.commit()
		
		try:
			cur.execute('''SELECT * FROM company WHERE name = %s;''', (companyName,))
		except:
			print("Error in selecting data")
		results = cur.fetchall()
		companyID = int(results[0][0])
		conn.commit()	

		#sending data to database
		for i in xrange(len(ownerNameList)):
			cur.execute('''INSERT INTO owner (owner_name, owner_data, owner_part, company_id)
				VALUES (%s, %s, %s, %s);''', (ownerNameList[i], ownerDataList[i], ownerSharesList[i], companyID))

		conn.commit()
		try:
			cur.execute('''SELECT owner_name, owner_data, owner_part FROM owner WHERE company_id = %s;''', (companyID,))
		except:
			print("Error in selecting data")
		ownerResults = cur.fetchall()

		conn.commit()
		conn.close()

		return render_template('newCompany.html', company=results[0], owners=ownerResults)

@app.route("/searchResults", methods=['POST'])
def searchAccount():
	searchResult = request.form['search']
	nameStr = str(searchResult)
	nameSrc = '%'+ nameStr+ '%'
	conn = connectDB()
	cur = conn.cursor()
	try:
		cur.execute('''SELECT DISTINCT company.company_id, name, regnr FROM company JOIN owner ON (company.company_id = owner.company_id)
			WHERE name LIKE %s OR regnr = %s OR owner_name LIKE %s;''', (nameSrc, nameStr, nameSrc))
	except:
		print("Error in selecting data")
	results = cur.fetchall()
	companyIdResult = int(results[0][0])
	conn.commit()
	conn.close()

	return render_template('searchResults.html', company=results)

@app.route("/company.html", methods=['GET'])
def showResults():
	companyId = int(request.args.get('id'))

	conn = connectDB()
	cur = conn.cursor()

	try:
		cur.execute('''SELECT name, regnr, regdate, capital FROM company WHERE company_id = %s;''', (companyId,))
	except:
		print("Error in selecting data")
	results = cur.fetchall()
	conn.commit()

	try:
		cur.execute('''SELECT owner_name, owner_data, owner_part FROM owner WHERE company_id = %s;''', (companyId,))
	except:
		print("Error in selecting data")
	ownerResults = cur.fetchall()
	
	conn.commit()
	conn.close()
	
	return render_template('company.html', company=results[0], owners=ownerResults)
	

if __name__ == "__main__":
	app.run(debug=True)
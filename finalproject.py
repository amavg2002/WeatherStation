################ ######################
## Team 13:
## name: Amauri Villegas Garcia
## name : Devin Q Quoc-An Pham
## name:  Zhengyi Zhu
## name: Ziqi Ding
########################################################

########### IMPORTS : ########################
import requests
from requests.exceptions import HTTPError
import json
import RPi.GPIO as GPIO
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
import time
from time import sleep, strftime
import Freenove_DHT as DHT
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from threading import Timer

############ setup  ###################
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

############  GLOBAL CONSTANST #####
TIMEOUT = 10 # 10 seconds to timeout irrigation while movement occurs
REFRESH_INTERVAL=4 # 10 seconds
CONNECT=60 #1 min
AVERAGE_INTERVAL=60 # 1 min
MAXWATER=1020 #maximum gallons of water per hour
IE=0.75 #IE constant
PF=1  #PF could be 1,.80,.5,.3
SF=200 # area to be irrigated
scheduler= BackgroundScheduler()
scheduler.start()
DHTPin=11  #define the pin of DHT11
PIRPIN = 32 #define the pin of PIR sensor
RELAYPIN = 12 #define the pin of Relay module
cimis_response={} #this dictionary will hold the response information from cimis api
tempList=[] #List that holds the values for temperature read by DHT11 sensor
avgtempL=[] # List that holds average values  for temp (determined every hour)
humidityList=[] #list that holds the values for humidity read by DHT11 sensor
avghumL=[]  # List that holds average humidity values (determined every hour)
tempAPiList=[] #List that holds the temp values from  API
humiAPiList=[] #List that holds the humidity values read  from API 
EtoAPiList=[]  #List that holds the Eto values from  API
ETolocal=[] #list to hold all the Etolocal calculated from website and  sensonr reading
Eto=-1 #this value is obtained by averaging the Etolocal list
response_success=False #boolean flag to determine when response from cimis is  false (couldn't communicate with server) or True( successfully communicated with server)


GPIO.setup(PIRPIN, GPIO.IN)
GPIO.setup(RELAYPIN, GPIO.OUT)


PCF8574_address=0x27 #I2C address of the PCF8574 chip
try:
    mcp=PCF8574_GPIO(PCF8574_address)
except:
    print("I2C Address Error! ")
    exit(1)
##Create LCD, passing in MCP gpio adapter
lcd= Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7],GPIO=mcp)

############################################### FUNCTIONS: #####################################################################

## Function in charge of calling cimis api and getting our data from station 75: ###
def call_Cimis_Api():
    global response_success
    global cimis_response
    print("+++++++++++++++++++++++++++++++++++++++++++++++")
    print("inside call_Cimis_Api(): ")
    url="http://et.water.ca.gov/api/data?appKey=55a1b0c5-298b-4fd5-9c42-2576c839580d&targets=75&startDate=2019-06-15&endDate=2019-06-15&unitOfMeasure=M&dataItems=hly-eto,hly-air-tmp,hly-rel-hum"
    try:
        response=requests.get(url,timeout=15,header={'Active': 'application/json'})
        #if the response was successful, no Exception will be raised
    except HTTPError as http_err:
	response_success=False
        print("HTTP error ocurred:",http_err)
    except Exception as err:
	response_success=False
        print("Other error occurred:", err)
    else:
	if(response):
		cimis_response=response.json() #turn cimis response into a pythong dict
		print("Success getting cimis info into python dict!")
        response_success=True
#    print("cimis_response_records  length=  ",len(cimis_response['Data']['Providers'][0]['Records']))


####### This function extracts the records inside cimis_response dictionary and it
##   sends it to temAPiList, humiAPiList, EtoAPiList:
def parse_cimisdict():
    global response_success
    global tempAPiList
    global humiAPiList
    global EtoAPiList
    if(response_success):
    	for index in range(0,len(cimis_response['Data']['Providers'][0]['Records'])):
		print("===================================================")
		print(index)
		if(cimis_response['Data']['Providers'][0]['Records'][index]['HlyAirTmp']['Value'] is not None):
			value.append(cimis_response['Data']['Providers'][0]['Records'][index]['HlyAirTmp']['Value'])
			print("value =" ,value)
			y=float(value)
        	tempAPiList.append(y)
		elif(cimis_response['Data']['Providers'][0]['Records'][index]['HlyRelHum']['Value'] is not None):
			value2.append(cimis_response['Data']['Providers'][0]['Records'][index]['HlyRelHum']['Value'])
			print("value2 =", value2)
			x=float(value2)
        	humiAPiList.append(x)
		elif(cimis_response['Data']['Providers'][0]['Records'][index]['HlyEto']['Value'] is not None):
			value3.append(cimis_response['Data']['Providers'][0]['Records'][index]['HlyEto']['Value'])
			print("value3 =", value3) 
			z=float(value3)
        	EtoAPiList.append(z)
    
    //print("TempAPiList length= ",len(tempAPiList))
	//print ("TempAPIlist: ",tempAPiList)
   	//print("humiAPiList length= ",len(humiAPiList))
	//print ("humiAPIlist: ",humiAPiList)
    //print("EtoAPiList length= ",len(EtoAPiList))
	//print ("EtoAPIlist: ",EtoAPiList)

    
##  This function   gets the average humidity from our DHT11  readings ###########
def get_Humidity_avg():
    print("humidity average: ")
    sum=0.0
    if (len(humidityList)>0):
        for y in humidityList:
            sum = sum+y
        return(round( (sum/ len(humidityList)),3))
    return 0.00

## This function  gets the average  temperature from our DHT11 readings #######
def get_Temp_avg():
    print("Temp average: ")
    sum=0.0
    if(len(tempList)>0):
        for x in tempList:
            sum=sum+x
        return (round((sum /len(tempList)),3))
    return 0.00

##  This function   gets the average humidity from our API data list  readings ###########
def get_HumidityAPI_avg():
    print("humidity average: ")
    sum=0.0
    if (len(humiAPiList)>0):
        for y in humiAPiList:
            sum = sum+y
        return(round( (sum/ len(humiApiList)),3))
    return 0.00

## This function  gets the average  temperature from API data list readings #######
def get_TempAPI_avg():
    print("Temp average: ")
    sum=0.0
    if(len(tempAPiList)>0):
        for x in tempAPiList:
            sum=sum+x
        return (round((sum /len(tempAPiList)),3))
    return 0.00


## This function  gets the average  Eto from API data list readings #######
def get_EtoApi():
    print("ETo average: ")
    sum=0.0
    if(len(EtoAPiList)>0):
        for x in EtoAPiList:
            sum=sum+x
        return (round((sum /len(EtoAPiList)),3))
    return 0.00

#### This function read temp and humidity from  DHT11 sensor and puts the values into list #######
def readTempandHum():
    print("Calling this function every %d seconds"  % REFRESH_INTERVAL)
    dht=DHT.DHT(DHTPin) #create a DHT class object
    sumCnt=0    #number of reading times
    sumCnt+=1 #counting number of reading time
    chk=dht.readDHT11() #read DHT11 and get a return value
    print ("The sumCnt is : %d, \t chk : %d"%(sumCnt,chk))
    if (chk is dht.DHTLIB_OK):  
        print ("DHT11,OK!")
        ##put it in the list of measurements
        tempList.append(dht.temperature)
        humidityList.append(dht.humidity)
    elif(chk is dht.DHTLIB_ERROR_CHECKSUM):
        print("DHTLIB_ERROR_CHECKSUM!")
    elif(chk is dht.DHTLIB_ERROR_TIMEOUT):
        print("DHTLIB_ERROR_TIMEOUT!")
    else:
        print ("OTHER error !")
    #print ("Humidity: , \t Temperature : \n",dht.humidity, dht.temperature)
    #print("---------------------------------\n")
    if(len(tempList)>0):
        for x in tempList:
            print(x)
    if(len(humidityList)>0):
        for x in humidityList:
            print(x)
    time.sleep(1)



############ This function clears the last thing on the lcd display after program termination ############################
def destroy():
    lcd.clear()

############ This function calculates the amount of time to irrigate based on variables ############################
def calculate(x):
        global MAXWATER #maximum gallons of water per hour
        global IE #IE constant
        global PF #PF could be 1,.80,.5,.3
        global SF # area to be irrigated
        # x = ET_0 value calculated from local and CIMIS values

        y = (x*PF*SF*0.62)/IE

        y = y/(24*MAXWATER)*3600

        return(y) #y = calculates how many seconds irrigation goes for

############ This function calculates the ETo local value based on local and CIMIS humidity data ############################
def EToValue(CIMISHumidity, CIMISETo, LocalHumidity, CIMISTemp, LocalTemp):
        ET = CIMISETo*(CIMISHumidity/LocalHumidity)*(LocalTemp/CIMISTemp)
        return(ET)
        

########## This Function  displays our home screen to lcd while program is running on background and no updates are being displayed ##############################
def displayHomescreen():
        #time.sleep(1)
        #curtime=time.time()-starttime
        #print("current  time: \n",curtime)
        lcd.setCursor(0,0) #set cursos position
        lcd.message("Weather Station\n") #display  main title of program
        lcd.message("sampling data..\n")
        lcd.noDisplay()
        sleep(1.1)
        lcd.display()
        lcd.message("\nsampling data..\n")
        #-lcd.DisplayLeft()


############ This function calls the function to turn on and off relay to simulate irrigation ############################
def irrigation():
        GPIO.add_event_detect(PIRPIN, GPIO.BOTH, loop)

############ This function when called turns on and off relay to simulate irrigation and accounts for motion detection ############################
def loop(PIRPIN):
        global TIMEOUT
        initial = 0
        start = time.time()
        while True:
                if GPIO.input(PIRPIN) == GPIO.HIGH:
                        if initial == 0:
                                GPIO.output(RELAYPIN, GPIO.HIGH)
                                print("Movement detected! Turning off irrigation...")
                                lcd.clear()
                                lcd.message("Motion  Detected\n Irrigation Off")
                                initial = initial + 1
                        if GPIO.input(PIRPIN) == GPIO.HIGH and time.time() - start > TIMEOUT: #change 10 to 60 seconds for actual testing
                                GPIO.output(RELAYPIN, GPIO.LOW)
                                print("Resuming irrigation...")
                                lcd.clear()
                                lcd.message("    Resuming \n   Irrigation")
                                break
                if GPIO.input(PIRPIN) == GPIO.LOW:
                        GPIO.output(RELAYPIN, GPIO.LOW)
                        print("No movement detected. Resuming irrigation...")
                        lcd.clear() 
                        lcd.message("   No  Motion   \n Irrigation  On")
                        break


########### This is the main function of our program ##############################
def main():
    global REFRESH_INTERVAL
    global connect_success
    global tempAPiList
    global humiAPiList
    global EtoAPiList
    global MAXWATER
    mcp.output(3,1) #turn on LCD backLight
    lcd.begin(16,2) #set number of lcd lines and columns
    starttime=time.time()
    #Now call every X  seconds
    scheduler.add_job(readTempandHum, 'interval', seconds=REFRESH_INTERVAL)
    scheduler.add_job(call_Cimis_Api, 'interval', seconds=CONNECT) #time.sleep(1)
    
    while True:
        curtime=time.time()-starttime
        print("current  time: \n", curtime)
        displayHomescreen()
	pase_cimisdict()
        if(connect_success): 
        	if (curtime>AVERAGE_INTERVAL):
            		print("Before displaying averages to LCD")
	            result=get_Humidity_avg() #get average humidity
        	    temp=get_Temp_avg() #get average tmp
	            avgtempL.append(temp) #add it to the avg temp list
        	    avghumL.append(result)  #add it to avg humidity list
	            print(temp,result)
	            lcd.clear()
	            lcd.message("Local Avg Humi:"+str(result)+"%\n") #display  lcd
	            lcd.message("Local Avg Temp:"+str(temp)+"C\n")  # display lcd
	            time.sleep(3)
	            lcd.clear()
	            REFRESH_INTERVAL +=4
	            starttime=time.time() #reset time
				humapi=get_HumidityAPI_avg()  #get the humidity from API reading List
				cimiseto=get_EtoApi()  #get the Eto from api reading List
				cimistemp=get_TempAPI_avg()  #get the Temp from api reading LIst
	            x = EToValue(humapi, cimiseto, result, cimistemp, temp) # calculates local ETo value
	            print("Local ETo:", x)
	            lcd.message("LocalETo:"+str(x)+"\n")
	            t = calculate(x)
	            print("Irrigation time:", t)
	            lcd.message("IrrigTime:"+str(t)+"s\n")
	            time.sleep(5)
	            lcd.clear()
	            g = (t/3600)/MAXWATER
	            f = 1020-g
	            lcd.message("Saving:"+str(f)+"\ngallons\n")
	            irrigation()
        	    break
        
if __name__ == '__main__':
        print("Program is Starting...")
        try: 
                main()
        except KeyboardInterrupt:
                destroy()
                GPIO.cleanup()
                exit()  





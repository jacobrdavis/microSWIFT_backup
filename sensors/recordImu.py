#! /usr/bin/python3

#standard imports 
import busio, board
import time, os, sys, math
from datetime import datetime
import numpy as np
import logging
from logging import *
from time import sleep

#third party imports
import RPi.GPIO as GPIO

#my imports 
from config3 import Config
import adafruit_fxos8700_microSWIFT
import adafruit_fxas21002c_microSWIFT

#---------------------------------------------------------------
configDat = sys.argv[1]
configFilename = configDat #Load config file/parameters needed

config = Config() # Create object and load file
ok = config.loadFile( configFilename )
if( not ok ):
    sys.exit(0)

#set up logging
logDir = config.getString('Loggers', 'logDir')
LOG_LEVEL = config.getString('Loggers', 'DefaultLogLevel')
#format log messages (example: 2020-11-23 14:31:00,578, recordIMU - info - this is a log message)
#NOTE: TIME IS SYSTEM TIME
LOG_FORMAT = ('%(asctime)s, %(filename)s - [%(levelname)s] - %(message)s')
#log file name (example: home/pi/microSWIFT/recordIMU_23Nov2020.log)
LOG_FILE = (logDir + '/' + 'recordIMU' + '_' + datetime.strftime(datetime.now(), '%d%b%Y') + '.log')
logger = getLogger('system_logger')
logger.setLevel(LOG_LEVEL)
logFileHandler = FileHandler(LOG_FILE)
logFileHandler.setLevel(LOG_LEVEL)
logFileHandler.setFormatter(Formatter(LOG_FORMAT))
logger.addHandler(logFileHandler)

#load parameters from Config.dat
#system parameters 
floatID = os.uname()[1]
#floatID = config.getString('System', 'floatID')

dataDir = config.getString('System', 'dataDir')
burst_interval=config.getInt('System', 'burst_interval')
burst_time=config.getInt('System', 'burst_time')
burst_seconds=config.getInt('System', 'burst_seconds')

bad = config.getInt('System', 'badValue')

#IMU parameters
imuFreq=config.getFloat('IMU', 'imuFreq')
imu_samples = imuFreq*burst_seconds
imu_gpio=config.getInt('IMU', 'imu_gpio')

#initialize IMU GPIO pin as modem on/off control
GPIO.setmode(GPIO.BCM)
GPIO.setup(imu_gpio,GPIO.OUT)
#turn IMU on for script recognizes i2c address
GPIO.output(imu_gpio,GPIO.HIGH)

"""
FXOS8700 accelerometer range values
ACCEL_RANGE_2G = 0x00
ACCEL_RANGE_4G = 0x01
ACCEL_RANGE_8G = 0x02

FXAS21002 gyro range values
GYRO_RANGE_250DPS   = 250
GYRO_RANGE_500DPS   = 500
GYRO_RANGE_1000DPS  = 1000
GYRO_RANGE_2000DPS  = 2000
"""

def init_imu():
    #initialize fxos and fxas devices (required after turning off device)
    logger.info('power on IMU')
    GPIO.output(imu_gpio,GPIO.HIGH)
    i2c = busio.I2C(board.SCL, board.SDA)
    fxos = adafruit_fxos8700_microSWIFT.FXOS8700(i2c, accel_range=0x00)
    fxas = adafruit_fxas21002c_microSWIFT.FXAS21002C(i2c, gyro_range=500)
    
    return fxos, fxas

# Optionally create the sensor with a different accelerometer range (the
# default is 2G, but you can use 4G or 8G values):
#sensor = adafruit_fxos8700.FXOS8700(i2c, accel_range=adafruit_fxos8700.ACCEL_RANGE_4G)
#sensor = adafruit_fxos8700.FXOS8700(i2c, accel_range=adafruit_fxos8700.ACCEL_RANGE_8G)
 
# Main loop will read the acceleration and magnetometer values every second
# and print them out.
imu = []
isample = 0


tStart = time.time()
#-------------------------------------------------------------------------------
#LOOP BEGINS
#-------------------------------------------------------------------------------
logger.info('---------------recordIMU.py------------------')
while True:
    
    
    now=datetime.utcnow()
    if  now.minute == burst_time or now.minute % burst_interval == 0 and now.second == 0:
        
        logger.info('initializing IMU')
        fxos, fxas = init_imu()
        logger.info('IMU initialized')
        
        logger.info('starting burst')
        
        #create new file for new burst interval 
        fname = dataDir + floatID + '_IMU_'+'{:%d%b%Y_%H%M%SUTC.dat}'.format(datetime.utcnow())
        logger.info('file name: %s' %fname)
             
        with open(fname, 'w',newline='\n') as imu_out:
            logger.info('open file for writing: %s' %fname)
            t_end = time.time() + burst_seconds #get end time for burst
            isample=0
            while time.time() <= t_end or isample < imu_samples:
        
                try:
                    accel_x, accel_y, accel_z = fxos.accelerometer
                    mag_x, mag_y, mag_z = fxos.magnetometer
                    gyro_x, gyro_y, gyro_z = fxas.gyroscope
                except Exception as e:
                    logger.info(e)
                    logger.info('error reading IMU data')
         
                timestamp='{:%Y-%m-%d %H:%M:%S}'.format(datetime.utcnow())

                imu_out.write('%s,%f,%f,%f,%f,%f,%f,%f,%f,%f\n' %(timestamp,accel_x,accel_y,accel_z,mag_x,mag_y,mag_z,gyro_x,gyro_y,gyro_z))
                imu_out.flush()
        
                isample = isample + 1
                
               
                if time.time() >= t_end and 0 < imu_samples-isample <= 40:
                    continue
                elif time.time() > t_end and imu_samples-isample > 40:
                    break
                
                #hard coded sleep to control recording rate. NOT ideal but works for now    
                sleep(0.065)
            
            logger.info('end burst')
            logger.info('IMU samples %s' %isample)  
            #turn imu off     
            GPIO.output(imu_gpio,GPIO.LOW)
            logger.info('power down IMU')
            

    
    sleep(.50)

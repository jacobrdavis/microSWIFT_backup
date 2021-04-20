#!usr/bin/python3
'''
This program runs data collection, processing, and telemetry for microSWIFT instruments.


@author alexdeklerk (Alex de Klerk)
'''

#imports
import logging

#my imports
import config3
import recordGPS
import recordIMU
import recordTemp
import recordVolt
import send_sbd
import process_data






if __name__ == '__main__':
    
    #load config file and get parameters
    configFile = sys.argv[1] #Load config file/parameters needed
    config = config3.Config() # Create object and load file
    ok = config.loadFile(configFile)
    if(not ok):
        print('Error loading config file')
        sys.exit(1)
        
    #system parameters
    floatID = config.getString('System', 'floatID') 
    dataDir = config.getString('System', 'dataDir')
    logDir = config.getString('Loggers', 'logDir')
    
    payload_type = config.getInt('System', 'payloadType')
    sensor_type = config.getInt('System', 'sensorType')
    port = config.getInt('System', 'port')
    badValue = config.getInt('System', 'badValue')
    numCoef = config.getInt('System', 'numCoef')
       
    burst_seconds = config.getInt('System', 'burst_seconds')
    burst_time = config.getInt('System', 'burst_time')
    burst_int = config.getInt('System', 'burst_interval')
    call_int = config.getInt('Iridium', 'call_interval')
    call_time = config.getInt('Iridium', 'call_time')
    
    #GPS parameters 
    gps_port = config.getString('GPS', 'port')
    startBaud = config.getInt('GPS', 'startBaud') #GPS default baud rate, if it has been reset
    baud = config.getInt('GPS', 'baud')
    gpsGPIO = config.getInt('GPS', 'gpsGPIO')
    gps_freq = config.getInt('GPS', 'GPS_frequency') #currently not used, hardcoded at 4 Hz (see init_gps function)
    gps_samples = gps_freq*burst_seconds
    gps_timeout = config.getInt('GPS','timeout')
   
    #Iridium parameters 
    modem_port = config.getString('Iridium', 'port')
    modem_baud = config.getInt('Iridium', 'baud')
    modemGPIO =  config.getInt('Iridium', 'modemGPIO')
    call_interval = config.getInt('Iridium', 'call_interval')
    call_time = config.getInt('Iridium', 'call_time')
    timeout = config.getInt('Iridium', 'timeout')
    
    #temperature parameters
    temp_interval = config.getFloat('Temp', 'interval')
    temp_samples = int(burst_seconds/temp_interval)
    CLK  = config.getInt('Temp', 'CLK')
    MISO = config.getInt('Temp', 'MISO')
    MOSI = config.getInt('Temp', 'MOSI')
    CS   = config.getInt('Temp', 'CS')
    
    #voltage parameters   
    volt_interval = config.getInt('Voltage', 'interval')
    volt_samples = int(burst_seconds/volt_interval)
    shuntOhms=config.getFloat('Voltage', 'shuntOhms')
    maxExpectedAmps=config.getFloat('Voltage', 'maxExpectedAmps')
    
    #set up logging
    LOG_LEVEL = config.getString('Loggers', 'DefaultLogLevel')
    #format log messages (example: 2020-11-23 14:31:00,578, recordGPS - info - this is a log message)
    #NOTE: TIME IS SYSTEM TIME
    LOG_FORMAT = ('%(asctime)s, %(filename)s - [%(levelname)s] - %(message)s')
    #log file name (example: home/pi/microSWIFT/recordGPS_23Nov2020.log)
    LOG_FILE = (logDir + '/' + 'microSWIFT' + floatID + '_' + datetime.strftime(datetime.now(), '%d%b%Y') + '.log')
    logger = getLogger('system_logger')
    logger.setLevel(LOG_LEVEL)
    logFileHandler = FileHandler(LOG_FILE)
    logFileHandler.setLevel(LOG_LEVEL)
    logFileHandler.setFormatter(Formatter(LOG_FORMAT))
    logger.addHandler(logFileHandler)
    
    logger.info("---------------microSWIFT.py------------------")
    logger.info('python version {}'.format(sys.version))
    
    
    




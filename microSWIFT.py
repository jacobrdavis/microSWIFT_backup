#!usr/bin/python3
'''
This program runs data collection, processing, and telemetry for microSWIFT instruments.


@author alexdeklerk (Alex de Klerk)
'''

#imports
import logging

#my imports
import recordGPS
import recordIMU
import recordTemp
import recordVolt
import send_sbd
import process_data






if __name__ == '__main__'

#set up logging to file



#load config file and get parameters
configFilename = sys.argv[1] #Load config file/parameters needed
config = Config() # Create object and load file
ok = config.loadFile( configFilename )
if( not ok ):
    logger.info ('Error loading config file: "%s"' % configFilename)
    sys.exit(1)


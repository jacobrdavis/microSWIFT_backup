#! /usr/bin/python3
"""
author: @erainvil

Description: This script is the main operational script that runs on the microSWIFT. It is the scheduler that runs the recording of the GPS
and IMU as well as schedules the processing scripts after they are done recording. 


"""

# Main import Statemennts
import concurrent.futures
import datetime
import numpy as np

# Import GPS functions
from GPS.recordGPS import recordGPS
from GPS.GPSwaves import GPSwaves
from GPS.GPStoUVZ import GPStoUVZ

# Import IMU functions
from IMU.recordIMU import recordIMU

# Import SBD functions
from SBD.sendSBD import createTX
from SBD.sendSBD import sendSBD
from SBD.sendSBD import checkTX

# Import from utils
from utils.config3 import Config

## ------------- Load Config file --------------------------------
# Define Config file name
configFilename = r'utils/Config.dat'
config = Config() # Create object and load file
ok = config.loadFile( configFilename )
if( not ok ):
	logger.info ('Error loading config file: "%s"' % configFilename)
	sys.exit(1)

#System parameters
dataDir = config.getString('System', 'dataDir')
floatID = os.uname()[1]
sensor_type = config.getInt('System', 'sensorType')
badValue = config.getInt('System', 'badValue')
numCoef = config.getInt('System', 'numCoef')
port = config.getInt('System', 'port')
payload_type = config.getInt('System', 'payloadType')
burst_seconds = config.getInt('System', 'burst_seconds')
burst_time = config.getInt('System', 'burst_time')
burst_int = config.getInt('System', 'burst_interval')
#Compute number of bursts per hour
num_bursts = int(60 / burst_int)

#GPS parameters
gps_fs = config.getInt('GPS', 'gps_frequency') #currently not used, hardcoded at 4 Hz (see init_gps function)

#IMU parameters
imu_fs = config.getFloat('IMU', 'imu_frequency')

#Compute number of bursts per hour
num_bursts = int(60 / burst_int)

#Generate lists of burst start and end times based on parameters from Config file
start_times = [burst_time + i*burst_int for i in range(num_bursts)]
end_times = [start_times[i] + burst_seconds/60 for i in range(num_bursts)] #could also use lambda
print('start times', start_times)
print('end times', end_times)

	
 # Start time of loop iteration
begin_script_time = datetime.datetime.now()
print('Starting up')
	
#Run following code unless importing as a module
if __name__ == "__main__":
	while True:
	
		#Get current minute of the hour expressed as a fraction
		now = datetime.utcnow().minute + datetime.utcnow().second/60
		
		for i in start_times:
			if now >= start_times[i] and now < end_times[i]: #Are we in a record window
				
				end_time = end_times[i]
				# Run recordGPS.py and recordIMU.py concurrently with asynchronous futures
				with concurrent.futures.ThreadPoolExecutor() as executor:
					# Submit Futures
					recordGPS_future = executor.submit(recordGPS, end_time)
					recordIMU_future = executor.submit(recordIMU, end_time)
			
					# get results from Futures
					GPSdataFilename = recordGPS_future.result()
					IMUdataFilename = recordIMU_future.result()
	
				## --------------- Data Processing Section ---------------------------------
				# Time processing section
				begin_processing_time = datetime.datetime.now()
				
				# Run processGPS
				# Compute u, v and z from raw GPS data
				u, v, z, lat, lon = GPStoUVZ(GPSdataFilename)
				
				# Compute Wave Statistics from GPSwaves algorithm
				Hs, Tp, Dp, E, f, a1, b1, a2, b2 = GPSwaves(u, v, z, GPS_fs)
				
				# Compute mean velocities, elevation, lat and lon
				u_mean = np.mean(u)
				v_mean = np.mean(v)
				z_mean = np.mean(z)
				lat_mean = np.mean(lat)
				lon_mean = np.mean(lon)
				
				# Temperature and Voltage recordings - will be added in later versions
				temp = 0
				volt = 0
				
				# End Timing of recording
				print('Processing section took', datetime.datetime.now() - begin_processing_time)
				
				# Run processIMU
				    # IMU data:
				    # read in IMU data from file 
				    # IMUtoXYZ(IMU data)
				    # XYZwaves( XYZ from above )
				    
				## -------------- Telemetry Section ----------------------------------
				# Create TX file from processData.py output from combined wave products
				TX_fname, payload_data = createTX(Hs, Tp, Dp, E, f, u_mean, v_mean, z_mean, lat_mean, lon_mean, temp, volt, configFilename)
				
				# Decode contents of TX file and print out as a check - will be removed in final versions
				checkTX(TX_fname)
				
				# Send SBD over telemetry
				sendSBD(payload_data, configFilename)
				
				# End Timing of entire Script
				print('microSWIFT.py took', datetime.datetime.now() - begin_script_time)
				
			else:
				continue
		

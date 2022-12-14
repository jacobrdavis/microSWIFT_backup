#!/usr/bin/python3
#
# Opens a serial connection with a RockBlock 9603 SBD modem and
# transmits binary data that is passed to the main function
# Data is converted into binary in this script and then seperated
# into 4 messages send out through iridium in  specified format.

# standard imports 
import serial, sys
#from logging import *
import struct
import numpy as np
import time
from datetime import datetime
from logging import *
import RPi.GPIO as GPIO
from time import sleep

import logging

from config3 import Config

#load config file and get parameters
configFilename = sys.argv[1] #Load config file/parameters needed
config = Config() # Create object and load file
ok = config.loadFile( configFilename )
if( not ok ):
    logger.info ('Error loading config file: "%s"' % configFilename)
    sys.exit(1)
    
burst_seconds = config.getInt('System', 'burst_seconds')   
burst_time = config.getInt('System', 'burst_time')
burst_int = config.getInt('System', 'burst_interval')
call_int = config.getInt('Iridium', 'call_interval')
call_time = config.getInt('Iridium', 'call_time')
    
call_duration = burst_int*60-burst_seconds #time between burst end and burst start to make a call

#Iridium parameters - fixed for now
modemPort = '/dev/ttyUSB0' #config.getString('Iridium', 'port')
modemBaud = 19200 #config.getInt('Iridium', 'baud')
modemGPIO =  16 #config.getInt('Iridium', 'modemGPIO')
formatType = 10 #config.getInt('Iridium', 'formatType')
call_interval = 60 #config.getInt('Iridium', 'call_interval')
call_time = 10 #config.getInt('Iridium', 'call_time')
timeout=60 #some commands can take a long time to complete

id = 0 #arbitrary message counter

#set up GPIO pins for modem control
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(modemGPIO,GPIO.OUT)

#logger = getLogger('system_logger.'+__name__)  
sbdlogger = logging.getLogger('send_sbd.py')
sbdlogger.setLevel(logging.INFO)

#set up logging to file or sdout:
LOG_FILE = ('/home/pi/microSWIFT/logs' + '/' + 'send_sbd' + '_' + datetime.strftime(datetime.now(), '%d%b%Y') + '.log')
sbdFileHandler = FileHandler(LOG_FILE)
sbdFileHandler.setLevel(logging.INFO)
sbdFileHandler.setFormatter(Formatter('%(asctime)s, %(name)s - [%(levelname)s] - %(message)s'))
sbdlogger.addHandler(sbdFileHandler)
#handler = logging.StreamHandler(sys.stdout)
#handler.setLevel(logging.INFO)
#format = logging.Formatter('%(asctime)s, %(name)s - [%(levelname)s] - %(message)s')
#handler.setFormatter(format)
#logger.addHandler(handler)


#open binary data file and return bytes
def open_bin(binfile):
    try:
        with open(binfile, 'rb') as f:
            bytes=bytearray(f.read())
    except FileNotFoundError:
        sbdlogger.info('file not found: {}'.format(binfile))   
    except Exception as e:
        sbdlogger.info('error opening file: {}'.format(e))
    return bytes

def init_modem():
   
    try:
        GPIO.output(modemGPIO,GPIO.HIGH) #power on GPIO enable pin
        sbdlogger.info('power on modem...')
        sleep(3)
        sbdlogger.info('done')
    except Exception as e:
        sbdlogger.info('error powering on modem')
        sbdlogger.info(e)
        
    #open serial port
    sbdlogger.info('opening serial port with modem at {0} on port {1}...'.format(modemBaud,modemPort))
    try:
        ser=serial.Serial(modemPort,modemBaud,timeout=timeout)
        sbdlogger.info('done')
    except serial.SerialException as e:
        sbdlogger.info('unable to open serial port: {}'.format(e))
        return ser, False
        sys.exit(1)
   
    sbdlogger.info('command = AT')
    if get_response(ser,'AT'): #send AT command
        sbdlogger.info('command = AT&F')
        if get_response(ser,'AT&F'): #set default parameters with AT&F command 
            sbdlogger.info('command = AT&K=0')  
            if get_response(ser,'AT&K=0'): #important, disable flow control
                sbdlogger.info('modem initialized')
                return ser, True
    else:
        return ser, False

def get_response(ser,command, response='OK'):
    ser.flushInput()
    command=(command+'\r').encode()
    ser.write(command)
    sleep(1)
    try:
        while ser.in_waiting > 0:
            r=ser.readline().decode().strip('\r\n')
            if response in r:
                sbdlogger.info('response = {}'.format(r))
                return True
            elif 'ERROR' in response:
                sbdlogger.info('response = ERROR')
                return False
    except serial.SerialException as e:
        sbdlogger.info('error: {}'.format(e))
        return False


#Get signal quality using AT+CSQF command (see AT command reference).
#Returns signal quality, default range is 0-5. Returns -1 for an error or no response
#Example modem output: AT+CSQF +CSQF:0 OK    
def sig_qual(ser, command='AT+CSQ'):
    ser.flushInput()
    ser.write((command+'\r').encode())
    sbdlogger.info('command = {} '.format(command))
    r=ser.read(23).decode()
    if 'CSQ:' in r:
        response=r[9:15]
        qual = r[14]
        sbdlogger.info('response = {}'.format(response))
        return int(qual) #return signal quality (0-5)
    elif 'ERROR' in r:
        sbdlogger.info('Response = ERROR')
        return -1
    elif r == '':
        sbdlogger.info('No response from modem')
        return -1
    else:
        sbdlogger.info('Unexpected response: {}'.format(r))  
        return -1

#send binary message to modem buffer and transmits
#returns true if trasmit command is sent, but does not mean a successful transmission
#checksum is least significant 2 bytes of sum of message, with higher order byte sent first
#returns false if anything goes wrong
def transmit_bin(ser,msg):
    
    bytelen=len(msg)
    sbdlogger.info('payload bytes = {}'.format(bytelen))
                    
    #check signal quality and attempt to send until timeout reached
            
    try:
        sbdlogger.info('Command = AT+SBDWB')
        ser.flushInput()
        ser.write(('AT+SBDWB='+str(bytelen)+'\r').encode()) #command to write bytes, followed by number of bytes to write
        sleep(0.25)
    except serial.SerialException as e:
        sbdlogger.info('Serial error: {}'.format(e))
        return False
    except Exception as e:
        sbdlogger.info('Error: {}'.format(e))
        return False
    
    r = ser.read_until(b'READY') #block until READY message is received
    if b'READY' in r: #only pass bytes if modem is ready, otherwise it has timed out
        sbdlogger.info('response = READY')
        sbdlogger.info('passing message to modem buffer')
        ser.flushInput()
        ser.write(msg) #pass bytes to modem
        sleep(0.25)
        
        #The checksum is the least significant 2-bytes of the summation of the entire SBD message. 
        #The high order byte must be sent first. 
        checksum=sum(msg) #calculate checksum value
        byte1 = (checksum >> 8).to_bytes(1,'big') #bitwise operation shift 8 bits right to get firt byte of checksum and convert to bytes
        byte2 = (checksum & 0xFF).to_bytes(1,'big')#bitwise operation to get second byte of checksum, convet to bytes
        sbdlogger.info('passing checksum to modem buffer')
        ser.write(byte1) #first byte of 2-byte checksum 
        sleep(0.25)
        ser.write(byte2) #second byte of checksum
        sleep(0.25)
        
        r=ser.read(3).decode() #read response to get result code from SBDWB command (0-4)
        try:
            r=r[2] #result code of expected response
            sbdlogger.info('response = {}'.format(r))
            
            if r == '0': #response of zero = successful write, ready to send
                sbdlogger.info('command = AT+SBDIX')
                ser.flushInput()
                ser.write(b'AT+SBDIX\r') #start extended Iridium session (transmit)
                sleep(5)
                ser.read(11)
                r=ser.readline().decode().strip('\r\n')  #get command response in the form +SBDIX:<MO status>,<MOMSN>,<MT status>,<MTMSN>,<MT length>,<MT queued>
                sbdlogger.info('response = {}'.format(r))
                
                if '+SBDIX: ' in r:
                    r=r.strip('+SBDIX:').split(', ')
                    #interpret response and check MO status code (0=success)
                    if int(r[0]) == 0:
                        sbdlogger.info('Message send success')
                        return True
                    else:
                        sbdlogger.info('Message send failure, status code = {}'.format(r[0]))
                        return False
                else:
                    sbdlogger.info('Unexpected response from modem')
                    return False
            elif r == '1':
                sbdlogger.info('SBD write timeout')
                return False
            elif r == '2':
                sbdlogger.info('SBD checksum does not match the checksum calculated by the modem')
                return False
            elif r == '3':
                sbdlogger.info('SBD message size is not correct')
                return False
            else:
                sbdlogger.info('Unexpected response from modem')
                return False   
        except IndexError:
            sbdlogger.info('Unexpected response from modem')
            return False
    else:
        sbdlogger('did not receive READY message')
        return False
    
#same as transmit_bin but sends ascii text using SBDWT command instead of bytes
def transmit_ascii(ser,msg):
 
    msg_len=len(msg)
    
    if msg_len > 340: #check message length
        sbdlogger.info('message too long. must be 340 bytes or less')
        return False
    
    if not msg.isascii(): #check for ascii text
        sbdlogger.info('message must be ascii text')
        return False
    
    try:  
        ser.flushInput()
        sbdlogger.info('command = AT+SBDWT')
        ser.write(b'AT+SBDWT\r') #command to write text to modem buffer
        sleep(0.25)
    except serial.SerialException as e:
        sbdlogger.info('serial error: {}'.format(e))
        return False
    except Exception as e:
        sbdlogger.info('error: {}'.format(e))
        return False
    
    r = ser.read_until(b'READY') #block until READY message is received
    if b'READY' in r: #only pass bytes if modem is ready, otherwise it has timed out
        sbdlogger.info('response = READY')
        ser.flushInput()
        ser.write((msg + '\r').encode()) #pass bytes to modem. Must have carriage return
        sleep(0.25)
        sbdlogger.info('passing message to modem buffer')
        r=ser.read(msg_len+9).decode() #read response to get result code (0 for successful save in buffer or 1 for fail)
        if 'OK' in r:
            index=msg_len+2 #index of result code
            r=r[index:index+1] 
            sbdlogger.info('response = {}'.format(r))        
            if r == '0':
                sbdlogger.info('command = AT+SBDIX')
                ser.flushInput()
                ser.write(b'AT+SBDIX\r') #start extended Iridium session (transmit)
                sleep(5)
                r=ser.read(36).decode()
                if '+SBDIX: ' in r:
                    r=r[11:36] #get command response in the form +SBDIX:<MO status>,<MOMSN>,<MT status>,<MTMSN>,<MT length>,<MT queued>
                    r=r.strip('\r') #remove any dangling carriage returns
                    sbdlogger.info('response = {}'.format(r)) 
                    return True
    else:
        return False
    

#MAIN
#
#Packet Structure
#<packet-type> <sub-header> <data>
#Sub-header 0:
#    ,<id>,<start-byte>,<total-bytes>:
#Sub-header 1 thru N:
#    ,<id>,<start-byte>:
#--------------------------------------------------------------------------------------------
def send_microSWIFT_50(payload_data):
    sbdlogger.info('sending microSWIFT telemetry (type 50)')
    
    global id
    payload_size = len(payload_data)
    
    #check for data
    if payload_size == 0:
        sbdlogger.info('Error: payload data is empty')
        return 
    
    if payload_size != 1245:
        sbdlogger.info('Error: unexpected number of bytes in payload data. Expected bytes: 1245, bytes received: {}'.format(payload_size))
        return
    
    index = 0 #byte index
    packet_type = 1 #extended message
        
    #split up payload data into packets    
    #first packet to send
    header = str(packet_type).encode('ascii') #packet type as as ascii number
    sub_header0 = str(','+str(id)+','+str(index)+','+str(payload_size)+':').encode('ascii') # ',<id>,<start-byte>,<total-bytes>:'
    payload_bytes0 = payload_data[index:325] #data bytes for packet 0
    packet0 = header + sub_header0 + payload_bytes0
    
    
    #second packet to send
    index = 325
    sub_header1 = str(','+str(id)+','+str(index)+':').encode('ascii') # ',<id>,<start-byte>,<total-bytes>:'
    payload_bytes1 = payload_data[index:653] #data bytes for packet 1    
    packet1 = header + sub_header1 + payload_bytes1         
    
    
    #third packet to send
    index = 653
    sub_header2 = str(','+str(id)+','+str(index)+':').encode('ascii') # ',<id>,<start-byte>,<total-bytes>:'
    payload_bytes2 = payload_data[index:981] #data bytes for packet 2
    packet2 = header + sub_header2 + payload_bytes2      
   
    
    #fourth packet to send
    index = 981
    sub_header3 = str(','+str(id)+','+str(index)+':').encode('ascii') # ',<id>,<start-byte>,<total-bytes>:'
    payload_bytes3 = payload_data[index:1245] #data bytes for packet 3
    packet3 = header + sub_header3 + payload_bytes3 
    
    message = [packet0, packet1, packet2, packet3] #list of packets
    ordinal = ['first', 'second', 'third', 'fourth']

    
    tend = time.time()+call_duration #get end time to stop attempting call
    while time.time() <= tend:
    
        #initialize modem
        ser, modem_initialized = init_modem()

        if not modem_initialized:
            sbdlogger.info('Modem not initialized')
            GPIO.output(modemGPIO,GPIO.LOW) #power off modem
            continue
        
        #send packets
        sbdlogger.info('Sending 4 packet message (50)')
        
        i=0
        signal=[]
        while time.time() <= tend:
            
            isignal = sig_qual(ser)
            if isignal < 0:
                continue
            else: 
                signal.append(isignal)
                i+=1
            
            if len(signal) >= 3 and np.mean(signal[i-3:i]) >= 3: #check rolling average of last 3 values, must be at least 3 bars
                signal.clear() #clear signal values
                i=0 #reset counter
                
                #attempt to transmit packets
                for i in range(4):
                    sbdlogger.info('Sending {} packet'.format(ordinal[i]))
                    issent  = False
                    while issent == False:
                        issent  = transmit_bin(ser,message[i])            
            
                #increment message counter for each completed message
                if id >= 99:
                     id = 0
                else:   
                    id+=1 
                      
                #turn off modem
                sbdlogger.info('Powering down modem')    
                GPIO.output(modemGPIO,GPIO.LOW)
                return

    #turn off modem
    sbdlogger.info('Send SBD timeout')
    sbdlogger.info('powering down modem')    
    GPIO.output(modemGPIO,GPIO.LOW)
   

def send_microSWIFT_51(payload_data):
    sbdlogger.info('sending microSWIFT telemetry (type 51)')
    
    global id
    payload_size = len(payload_data)
    
    #check for data
    if payload_size == 0:
        sbdlogger.info('Error: payload data is empty')
        return 
    
    if payload_size != 249:
        sbdlogger.info('Error: unexpected number of bytes in payload data. Expected bytes: 249, bytes received: {}'.format(payload_size))
        return
    
    #split up payload data into packets    
    index = 0 #byte index
    packet_type = 0 #single packet
    
    #packet to send
    header = str(packet_type).encode('ascii') #packet type as as ascii number
    sub_header0 = str(','+str(id)+','+str(index)+','+str(payload_size)+':').encode('ascii') # ',<id>,<start-byte>,<total-bytes>:'
    payload_bytes0 = payload_data[index:248] #data bytes for packet
    packet0 = header + sub_header0 + payload_bytes0
    
    tend = time.time()+call_duration #get end time to stop attempting call
    while time.time() <= tend:
    
        #initialize modem
        ser, modem_initialized = init_modem()

        if not modem_initialized:
            sbdlogger.info('Modem not initialized')
            GPIO.output(modemGPIO,GPIO.LOW) #power off modem
            continue
        
        #send packets
        sbdlogger.info('Sending single packet message (51)')
        
        i=0
        signal=[]
        while time.time() <= tend:
            
            isignal = sig_qual(ser)
            if isignal < 0:
                continue
            else: 
                signal.append(isignal)
                i+=1
            
            if len(signal) >= 3 and np.mean(signal[i-3:i]) >= 3: #check rolling average of last 3 values, must be at least 3 bars
                signal.clear() #clear signal values
                i=0 #reset counter
                
                #attempt to transmit packet            
                success = transmit_bin(ser,packet0)
            
                if success == True: #increment message counter for each completed message
                    if id >= 99:
                         id = 0
                    else:   
                        id+=1 
                      
                    #turn off modem
                    sbdlogger.info('Powering down modem')    
                    GPIO.output(modemGPIO,GPIO.LOW)
                    return
             
                else: 
                    continue
 
    #turn off modem
    sbdlogger.info('Send SBD timeout')
    sbdlogger.info('powering down modem')    
    GPIO.output(modemGPIO,GPIO.LOW)
    



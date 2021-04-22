#!usr/bin/python3

import sys

sys.path.append('C:\\Users\\Alex de Klerk\\Documents\\GitHub\\microSWIFT\\utils\\')

import config3
import configparser

configFile='C:\\Users\\Alex de Klerk\\Documents\\GitHub\\microSWIFT\\config.dat'

cfg=configparser.ConfigParser()
cfg.read(configFile)
print(cfg.sections())

#cfg = config3.Config() # Create object and load file
#
#ok = cfg.loadFile(configFile)


print(cfg.items('Loggers'))
print(cfg.__dict__)
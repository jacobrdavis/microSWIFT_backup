#!usr/bin/python3

import sys

sys.path.append('C:\\Users\\Alex de Klerk\\Documents\\GitHub\\microSWIFT\\utils\\')

import configparser

configFile='C:\\Users\\Alex de Klerk\\Documents\\GitHub\\microSWIFT\\config.dat'

cfg=configparser.ConfigParser()
cfg.read(configFile)

sections = cfg.sections()
print(sections)
for name in sections:
    print(cfg.options(name))
    
class microSWIFT:
    
    def __init__(self):
        return 
    
    
    




#cfg = config3.Config() # Create object and load file
#
#ok = cfg.loadFile(configFile)


print(cfg.items('Loggers'))

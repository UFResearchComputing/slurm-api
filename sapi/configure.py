#/* ************************************************************************* */
#/*                                                                           */
#/*                   Configuration Class and Methods                         */
#/*                                                                           */
#/* ************************************************************************* */
from json import dumps
import configparser
import os

class configure(object):
  def __init__(self):
    #/* config path selection and read */
    self.config_path = '/etc/sapi/sapi.conf'
    if os.getenv("SAPI_CONFIG"):
      self.config_path = os.getenv("SAPI_CONFIG")
    try:
      config = configparser.ConfigParser()
      config.read(self.config_path)
    except Exception as e:
      raise ValueError("error reading configuration " + str(self.config_path) + ": " + str(e))
    for section in ['api','logging','ssl','auth']:
      if not section in config.sections():
        raise ValueError("missing required config section '" + section + '"')
    #/* [api] setttings */
    self.host        = config.get('api','host',fallback='0.0.0.0')
    self.port        = config.get('api','port',fallback='9090')
    self.debug       = config.getboolean('api','debug',fallback=False)
    self.version     = 1
    self.tmp         = config.get('api','tmp',fallback='/tmp')
    self.sbatch      = config.get('api','sbatch',fallback='sbatch')
    self.scancel     = config.get('api','scancel',fallback='scancel')
    #/* [logging] settings */
    self.log_file    = config.get('logging','path',fallback='/var/log/sapi.log')
    if self.debug:
      self.log_level = 'DEBUG'
    else:
      self.log_level = 'INFO'
    self.logger      = False # this gets set so we can pass a logger file to helper methods 
    #/* [ssl] setttings */
    self.use_ssl     = config.getboolean('ssl','enable',fallback=False)
    self.ssl_cert    = config.get('ssl','cert',fallback='/etc/sapi/ssl/sapi.cert')
    self.ssl_key     = config.get('ssl','key',fallback='/etc/sapi/ssl/sapi.key')
    #/* [auth] settings */
    self.issuer      = config.get('auth','jwt_issuer',fallback='sapi') 
    self.secret      = config.get('auth','jwt_secret',fallback='changeme')
    self.lifetime    = config.get('auth','jwt_lifetime',fallback=3600)
    self.algorithm   = config.get('auth','jwt_algorithm',fallback='HS256')

    #/* environment overrides and logic based settings */
    if os.getenv("SAPI_LOG"):
      self.log_file = os.getenv("SAPI_LOG")
     

  def __str__(self):
    result = {
      'host':        str(self.host),      
      'port':        str(self.port),      
      'log_file':    str(self.log_file), 
      'tmp':         str(self.tmp),
      'log_level':   str(self.log_level), 
      'debug':       str(self.debug), 
      'use_ssl':     str(self.use_ssl),   
      'ssl_cert':    str(self.ssl_cert),
      'ssl_key':     str(self.ssl_key),
      'sbatch':      str(self.sbatch),
      'scancel':     str(self.scancel),
      'issuer':      str(self.issuer),
      'secret':      str(self.secret),
      'lifetime':    str(self.lifetime),
      'algorithm':   str(self.algorithm)
    }
    return(dumps(result)) 

#!/usr/bin/env python36

#/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */
#/*                                                                          */
#/*                               slurm-api                                  */
#/*                               ---------                                  */
#/*                                                                          */
#/* Author: UFIT Research Computing                                          */
#/* Contact: support@rc.ufl.edu                                              */
#/* URL: https://gitlab.ufhpc/whowell/slurm-api                              */
#/* Description:                                                             */
#/*    slurm-api provides a RESTful API utilizing pyslurm library            */
#/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */


#/* ************************************************************************ */
#/*                                                                          */
#/*                             Dependencies                                 */
#/*                                                                          */
#/* ************************************************************************ */
import configparser
import re
import pyslurm
import os
import logging
import subprocess
import tempfile
from flask import Flask, request, g
from flask_restful import reqparse, abort, Resource, Api
from json import dumps, loads
from flask_jsonpify import jsonify
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy, Model
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
from flask_httpauth import HTTPTokenAuth
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, String
from logging.config import dictConfig
from pwd import getpwnam


#/* ************************************************************************ */
#/*                                                                          */
#/*                          Flask Initialization                            */
#/*                                                                          */
#/* ************************************************************************ */
#/* ****                          */
#/* ****  Flask Initialization    */
#/* ****                          */
app = Flask(__name__)
Base = declarative_base()
auth = HTTPTokenAuth(scheme='Token')
CORS(app)
# /* these are defaults which we override later */
app.config['SECRET_KEY'] = 'slurm-api'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/slurm-api.db'
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
#logfile = logging.getLogger('file')

#/* ************************************************************************ */
#/*                                                                          */
#/*                   Configuration Class and Methods                        */
#/*                                                                          */
#/* ************************************************************************ */
class ConfigureAPI(object):
  def __init__(self):
    #/* config path selection and read */
    self.config_path = '/etc/slurm-api.ini'
    if os.getenv("SLURM_API_CONFIG"):
      self.config_path = os.getenv("SLURM_API_CONFIG")
    try:
      config = configparser.ConfigParser()
      config.read(self.config_path)
    except Exception as e:
      raise ValueError("error reading configuration " + str(self.config_path) + ": " + str(e))
    for section in ['api','logging','authentication','ssl']:
      if not section in config.sections():
        raise ValueError("missing required config section '" + section + '"')
    #/* [api] setttings */
    self.host        = config.get('api','host',fallback='0.0.0.0')
    self.port        = config.get('api','port',fallback='5000')
    self.debug       = config.getboolean('api','debug',fallback=False)
    self.version     = 1
    self.tmp         = config.get('api','tmp',fallback='/tmp')
    self.sbatch      = config.get('api','sbatch',fallback='/opt/slurm/bin/sbatch')
    #/* [logging] settings */
    self.log_file    = config.get('logging','path',fallback='/opt/slurm-api/slurm-api.log')
    if self.debug:
      self.log_level = 'DEBUG'
    else:
      self.log_level = 'INFO'
    self.logger      = False # this gets set so we can pass a logger file to helper methods 
    #/* [ssl] setttings */
    self.use_ssl     = config.getboolean('ssl','enable',fallback=False)
    self.ssl_cert    = config.get('ssl','cert',fallback='/opt/slurm-api/conf/slurm-api.cert')
    self.ssl_key     = config.get('ssl','key',fallback='/opt/slurm-api/conf/slurm-api.key')
    #/* [auth] settings */
    self.enable_auth = config.get('authentication','enable',fallback=True)
    self.database    = config.get('authentication','database',fallback='/opt/slurm-api/slurm-api.db')
    self.database    = "sqlite:///" + self.database
    self.key         = config.get('authentication','key',fallback='slurm-api')
    self.expiration  = 31536000
    #/* environment overrides and logic based settings */
    if os.getenv("SLURM_API_LOG"):
      self.log_file = os.getenv("SLURM_API_LOG")
     

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
      'enable_auth': str(self.enable_auth),
      'key':         str(self.key),
      'database':    str(self.database),
      'sbatch':      str(self.sbatch)
    }
    return(dumps(result)) 

#/* ************************************************************************ */
#/*                                                                          */
#/*                        General Helper Methods                            */
#/*                                                                          */
#/* ************************************************************************ */
def searchDict(original_dict,request_string):
  new_dict = {}
  search = { 'key': '', 'value': '' };
  try:
    search_string = re.findall(r'\S+~\S+',request_string)[0]
    search_components = re.split(r'~',search_string)
    search_key = str(search_components[0])
    search_value = str(search_components[1])
    search = { 'key': search_key, 'value': search_value, 'string': search_string };
  except:
    pass
  if search['key'] and search['value']:
    for data_name,data in original_dict.items():
      if search['key'] in data and re.search(r"%s" % search['value'], dumps(data[search['key']])):
        new_dict[data_name] = data
      elif search['key'] == 'name' and re.search(r"%s" % search['value'], str(data_name)):
        new_dict[data_name] = data
  return new_dict

def filterResults(data,request,settings): 
  results = []
  if not isinstance(data,list):
    return False
  search_dict = request.args.to_dict()
  new_data = []
  for obj in data:
    if not isinstance(obj,dict): #just bomb out and don't modify if unexpected format for data
      return False
    obj_match_count = 0
    i = 0
    for search_key,search_value in search_dict.items():
      i = i + 1
      if search_key in obj and str(obj[search_key]) == str(search_value):
        obj_match_count = obj_match_count + 1
    if obj_match_count == i:
      new_data.append(obj)
  if settings.logger:
    settings.logger.debug("filterResults(): found " + str(len(new_data)) + " of " + str(len(data)) + " matching objects")
  return new_data



class apiError(Exception):
  def __init__(self,message,status_code=500,payload=None):
    Exception.__init__(self)
    self.message = message
    self.status_code = status_code
    self.payload = payload

  def to_dict(self):
    rv = dict(self.payload or ())
    rv['message'] = self.message
    return rv

#/* ************************************************************************ */
#/*                                                                          */
#/*                     Internal Auth Database Models                        */
#/*                                                                          */
#/* ************************************************************************ */
class APIUser(db.Model):
  __tablename__ = 'users'
  id = Column(Integer, primary_key=True)
  name = Column(String(256), index=True)
  administrator = Column(Integer)
  token = Column(String(256))

  def to_dict(self):
    api_user = {"id": self.id, "name": self.name, "administrator": self.administrator, "token": self.token}
    return api_user

  def __str__(self):
    api_user = {"id": self.id, "name": self.name, "administrator": self.administrator, "token": self.token}
    return dumps(api_user)

  def get(self):
    result = {}
    db_users = self.query.all()
    for db_user in db_users:
      if self.id == db_user.id or self.name == db_user.name:
        result = {"id": db_user.id, "name": db_user.name, "administrator": db_user.administrator, "token": db_user.token}  
        self.id = db_user.id
        self.name = db_user.name
        self.administrator = db_user.administrator
        self.token = db_user.token
    return True

  def get_all(self):
    result = []
    db_users = self.query.all()
    for db_user in db_users:
      result.append({"id": db_user.id, "name": db_user.name, "administrator": db_user.administrator, "token": db_user.token})  
    return result

  def generate_token(self):
    serial = Serializer(settings.key,expires_in = settings.expiration)
    if not self.administrator or self.administrator < 1:
      routes = { 
        "jobs": [ "get", "post", "put", "delete" ], 
        "partitions": ["get"], 
        "reservations": ["get"], 
        "nodes": ["get"], 
        "node": ["get"] 
      }
      restrict = True
    else:
      routes = { 
        "jobs": [ "get", "post", "put", "delete" ], 
        "job": [ "get", "post","put","delete" ], 
        "partitions": ["get","post","put","delete"], 
        "reservations": ["get","post","put","delete"], 
        "nodes": ["get"], 
        "node": ["get"], 
        "users": ["get","put","post","delete"],
        "user": ["get","put","post","delete"],
        "permissions": ["get","put","post","delete"],
        "permission": ["get","put","post","delete"],
        "token": ["get","put","post","delete"]
      }
      restrict = False
    payload = { "user": self.name, "routes": routes, "restrict": restrict }
    serial_set = serial.dumps(payload)
    self.token = str(serial_set.decode("utf-8"))
    return True

  def validate(self,admin=False):
    all_users = self.get_all()
    validated = False
    for try_user in all_users:
      if try_user.name == self.name and try_user.token == self.token:
        if not admin:
          validated = True
        elif try_user.admin:
          validated = True
    return validated

  def update(self):
    db.session.merge(self)
    db.session.commit()
    return True

  def exists(self):
    all_users = self.get_all()
    exist = False
    for try_user in all_users:
      if try_user.name == self.name:
        exist = True 
    return exist
     

class APIPermission(db.Model):
  __tablename__ = 'permissions'
  id = Column(Integer, primary_key=True)
  endpoint = Column(String(256), index=True)
  action = Column(String(256), index=True)

  def to_dict(self):
    api_perm = {"id": self.id, "endpoint": self.endpoint, "action": self.action}
    return api_perm

  def __str__(self):
    api_perm = {"id": self.id, "endpoint": self.endpoint, "action": self.action}
    return dumps(api_perm)

  def get(self):
    result = {}
    db_perms = self.query.all()
    for db_perm in db_perms:
      if self.id == db_perm.id: 
        result = {"id": db_perm.id, "endpoint": db_perm.endpoint, "action": db_perm.action} 
      elif self.endpoint == db_perm.endpoint and self.action == db_perm.action:
        result = {"id": db_perm.id, "endpoint": db_perm.endpoint, "action": db_perm.action} 
    return result

  def get_all(self):
    result = []
    db_perms = self.query.all()
    for db_perm in db_perms:
      result.append({"id": db_perm.id, "endpoint": db_perm.endpoint, "action": db_perm.action})  
    return result

  def update(self):
    db.session.merge(self)
    db.session.commit()
    return True

class APIUserPermission(db.Model):
  __tablename__ = 'user_permissions'
  id = Column(Integer, primary_key=True)
  user_id = Column(Integer, index=True)
  permission_id = Column(Integer, index=True)

  def to_dict(self):
    user_perm = {"id": self.id, "user_id": self.user_id, "permission_id": self.permission_id}
    return user_perm

  def __str__(self):
    user_perm = {"id": self.id, "user_id": self.user_id, "permission_id": self.permission_id}
    return dumps(api_perm)

  def get(self):
    result = {}
    user_perm = self.query.all()
    for user_perm in user_perms:
      if self.id == user_perm.permission_id: 
        result = {"id": user_perm.id, "user_id": user_perm.user_id, "permission_id": user_perm.permission_id} 
    return result

  def get_all(self):
    result = []
    user_perms = self.query.all()
    for user_perm in user_perms:
      result = {"id": user_perm.id, "user_id": user_perm.user_id, "permission_id": user_perm.permission_id} 
    return result

  def update(self):
    db.session.merge(self)
    db.session.commit()
    return True

def authValidate(request,action,endpoint):
  if request.headers.get('user') is None or request.headers.get('token') is None:
    return False
  test_user = APIUser()
  test_user.name = request.headers.get('user')
  test_user.get()
  passed_token = request.headers.get('token')
  if passed_token != test_user.token:
    return False
  serial = Serializer(settings.key,expires_in = settings.expiration)
  try:
    decoded = serial.loads(test_user.token,return_header=True)
  except:
    logging.debug("authValidate(): token decoding failed for user " + test_user.name + " which sometimes means the token is expired")
    return False
  if not decoded[0]["routes"]:
    logging.debug("authValidate(): bad token for user " + test_user.name)
    return False
  if not endpoint in decoded[0]["routes"]:
    logging.debug("authValidate(): user " + test_user.name + " does not have " + endpoint + " permissions")
    return False
  can_use_method = False
  for meth in decoded[0]["routes"][endpoint]:
    if meth == action:
      can_use_method = True
  if not can_use_method:
    return False 
  return True


#/* ************************************************************************ */
#/*                                                                          */
#/*                           REST API Endpoints                             */
#/*                                                                          */
#/* ************************************************************************ */
class nodes(Resource):
  def get(self):
    result = {'data':[],'count':0}
    action = 'get'
    endpoint = 'nodes'
    if not authValidate(request,action,endpoint):
      abort(403)   
    nodes_o = pyslurm.node()
    nodes = nodes_o.get()
    for label,node in nodes.items():
      result['data'].append(node)
    filtered_nodes = filterResults(result['data'],request,settings)
    if filtered_nodes != False:
      result['data'] = filtered_nodes
    result['count'] = len(result['data'])
    return jsonify(result)

class node(Resource):
  def get(self,name):
    result = {'data':[],'count':0}
    action = 'get'
    endpoint = 'node'
    if not authValidate(request,action,endpoint):
      abort(403)   
    nodes_o = pyslurm.node()
    nodes = nodes_o.get_node(name)
    for label,node in nodes.items():
      result['data'].append(node)
    filtered_nodes = filterResults(result['data'],request,settings)
    if filtered_nodes != False:
      result['data'] = filtered_nodes
    result['count'] = len(result['data'])
    return jsonify(result)

class partitions(Resource):
  def get(self):
    result = {'data':[],'count':0}
    action = 'get'
    endpoint = 'partitions'
    if not authValidate(request,action,endpoint):
      abort(403)   
    partition_o = pyslurm.partition()
    partitions = partition_o.get()
    for label,partition in partitions.items():
      result['data'].append(partition)
    filtered_partitions = filterResults(result['data'],request,settings)
    if filtered_partitions != False:
      result['data'] = filtered_partitions
    result['count'] = len(result['data'])
    return jsonify(result)

class reservations(Resource):
  def get(self):
    result = {'data':[],'count':0}
    action = 'get'
    endpoint = 'reservations'
    if not authValidate(request,action,endpoint):
      abort(403)   
    reservation_o = pyslurm.reservation()
    reservations = reservation_o.get()
    for label,reservation in reservations.items():
      result['data'].append(reservation)
    filtered_reservations = filterResults(result['data'],request,settings)
    if filtered_reservations != False:
      result['data'] = filtered_reservations
    result['count'] = len(result['data'])
    return jsonify(result)

class jobs(Resource):
  def get(self):
    result = {'data':[],'count':0}
    action = 'get'
    endpoint = 'jobs'
    #if not authValidate(request,action,endpoint):
    #  abort(403)   
    job_o = pyslurm.job()
    uid = getpwnam(request.headers.get('user')).pw_uid
    try:
      jobs = job_o.find_user(uid)
    except Exception as e:
      logfile.error("(" + endpoint + ") [" + action + "]: failure in search for user " + request.headers.get('user'))
      abort(500)
    for label,job in jobs.items():
      result['data'].append(job)
    filtered_jobs = filterResults(result['data'],request,settings)
    if filtered_jobs != False:
      result['data'] = filtered_jobs 
    result['count'] = len(result['data'])
    return jsonify(result)

  def post(self):
    result = {'data':[],'count':0}
    action = 'post'
    endpoint = 'jobs'
    if not authValidate(request,action,endpoint):
      abort(403)   
    job_spec = request.get_json(force=True)
    if 'uid' in job_spec and job_spec['uid'] !=  getpwnam(request.headers.get('user')).pw_uid:
      logfile.warn("(" + endpoint + ") [" + action + "]: user " + request.headers.get('user') + " tried to submit job for uid " + str(job_spec['uid']))
      abort(403)
    # set uid/gid based on user in request header
    job_spec['uid'] = getpwnam(request.headers.get('user')).pw_uid
    job_spec['gid'] = getpwnam(request.headers.get('user')).pw_gid
    old_dir = os.getcwd()
    os.chdir(settings.tmp)
    #- translate arguments we allow -#
    job_args = [] 
    allow = ['uid','gid','account','ntasks','cpus_per_task','mem_per_cpu','mem','reservation','partition','error','output','work_dir','nodes','nodelist','time']
    for k,v in job_spec.items():
      if k in allow:
        job_arg = '--' + str(k) + '=' + str(v)
        job_arg = re.sub("_","-",job_arg)
        job_args.append(job_arg)
    # form a job script from wrap #
    if not 'wrap' in job_spec:
      abort(400)
    tempfile.tempdir = settings.tmp
    batch_script = False
    try:
      batch_script = tempfile.NamedTemporaryFile(prefix="slurm-api-wrap_",suffix=".sh",mode='w+t',delete=False)
    except:
      logfile.error("(" + endpoint + ") [" + action + "]: failure opening new tempfile")
      abort(500)
    try: 
      batch_script.writelines('#!/bin/bash' + "\n")
      batch_script.writelines(job_spec['wrap'] + "\n")
    except:
      logfile.error("(" + endpoint + ") [" + action + "]: failure writing temporary batch script")
      abort(500)
    try:
      os.chown(batch_script.name, job_spec['uid'], job_spec['gid'])
    except Exception as e:
      logfile.error("(" + endpoint + ") [" + action + "]: failure setting ownership on " + batch_script.name + "\n" + str(e))
    try:
      os.chmod(batch_script.name, 0o640)
    except Exception as e:
      logfile.error("(" + endpoint + ") [" + action + "]: failure setting permissions on " + batch_script.name + "\n" + str(e))
    if batch_script:
      batch_script.close()

    # submit batch script #
    batch_submit = [settings.sbatch] + job_args
    batch_submit.append(batch_script.name)
    batch_command_string = ' '.join(batch_submit)
    logfile.debug("(" + endpoint + ") [" + action + "]: submitting job as " + batch_command_string)
    try:
      submit_out = subprocess.check_output(batch_submit).decode('utf-8').rstrip()
    except:
      logfile.error("(" + endpoint + ") [" + action + "]: failure submitting " + batch_script.name)
      abort(500)
    
    # try to get details of job back from api #
    job_id = False
    for line in submit_out.split("\n"):
      logfile.debug("[[ TESTING ]]:      " + line)
      if re.match("Submitted batch job \d+",line):
        logfile.debug("[[ TESTING ]]:         - matched test")
        job_id = line.split()[-1]
        logfile.debug("[[ TESTING ]]:         - jobid " + job_id)

    if job_id:
      job_o = pyslurm.job()
      job_search = job_o.find_id(job_id)
      for job in job_search:
        result['data'].append(job)
    else:
      result['data'] = [] 
    result['count'] = len(result['data'])
    os.chdir(old_dir)
    if batch_script:
      batch_script.close() 
    return jsonify(result)

class job(Resource):
  def get(self,id):
    result = {'data':[],'count':0}
    action = 'get'
    endpoint = 'jobs'
    #if not authValidate(request,action,endpoint):
    #  abort(403)   
    job_o = pyslurm.job()
    uid = getpwnam(request.headers.get('user')).pw_uid
    try:
      jobs = job_o.find_user(uid)
    except Exception as e:
      logfile.error("(" + endpoint + ") [" + action + "]: failure in search for user " + request.headers.get('user'))
      abort(500)
    for label,job in jobs.items():
      if int(job['job_id']) == int(id):
        result['data'].append(job)
    filtered_jobs = filterResults(result['data'],request,settings)
    if filtered_jobs != False:
      result['data'] = filtered_jobs 
    result['count'] = len(result['data'])
    return jsonify(result)

class users(Resource):
  def get(self):
    result = {"count": 0, "data": []}
    action = 'get'
    endpoint = 'users'
    if not authValidate(request,action,endpoint):
      abort(403)   
    nodes_o = pyslurm.node()
    api_user = APIUser()
    result['data'] = api_user.get_all()
    result['count'] = len(result['data'])
    return jsonify(result)

  def post(self):
    result = {"count": 0, "data": []}
    action = 'post'
    endpoint = 'users'
    if not authValidate(request,action,endpoint):
      abort(403)   
    nodes_o = pyslurm.node()
    user_data = request.get_json(force=True)
    new_user = APIUser()
    logfile.debug("(" + endpoint + ") checking for name in request data")
    if not user_data["name"] is None:
      new_user.name = user_data["name"]
    else:
      abort(400)
    logfile.debug("(" + endpoint + ") checking for admin level in request data")
    if not user_data["administrator"] is None:
      new_user.administrator = user_data["administrator"]
    logfile.debug("(" + endpoint + ") generating token")
    new_user.generate_token()
    logfile.debug("(" + endpoint + ") adding user")
    new_user.update()
    logfile.debug("(" + endpoint + ") gathering new user details")
    new_user.get()
    new_user_dict = new_user.to_dict()
    result['data'].append(new_user_dict)
    result['count'] = len(result['data'])
    return jsonify(result)

class user(Resource):
  def get(self,name):
    result = {"count": 0, "data": []}
    action = 'get'
    endpoint = 'users'
    if not authValidate(request,action,endpoint):
      abort(403)   
    nodes_o = pyslurm.node()
    api_user = APIUser()
    api_user.name = name
    api_user.get()
    api_user = api_user.to_dict()
    result['data'].append(api_user)
    result['count'] = len(result['data'])
    return jsonify(result)

class permissions(Resource):
  def get(self):
    result = {"count": 0, "data": []}
    action = 'get'
    endpoint = 'permissions'
    if not authValidate(request,action,endpoint):
      abort(403)   
    nodes_o = pyslurm.node()
    api_perm = APIPermission()
    result['data'] = api_perm.get_all()
    result['count'] = len(result['data'])
    return jsonify(result)

class permission(Resource):
  def get(self,id):
    result = {"count": 0, "data": []}
    action = 'get'
    endpoint = 'permissions'
    if not authValidate(request,action,endpoint):
      abort(403)   
    nodes_o = pyslurm.node()
    api_perm = APIPermission()
    api_perm.id = id
    result['data'].append(api_perm.get())
    result['count'] = len(result['data'])
    return jsonify(result)

class decode_token(Resource):
  def get(self,token):
    if not authValidate(request,action,endpoint):
      abort(403)   
    nodes_o = pyslurm.node()
    serial = Serializer(settings.key,expires_in = settings.expiration)
    decoded = serial.loads(token,return_header=True)
    return jsonify(decoded)
    
  

#/* ************************************************************************ */
#/*                                                                          */
#/*                                __MAIN__                                  */
#/*                                                                          */
#/* ************************************************************************ */
if __name__ == '__main__':
     #/* ****                          */
     #/* ****  General Configuration   */
     #/* ****                          */
     try:
       settings = ConfigureAPI()
     except Exception as e:
       print("Configuration Error: " + str(e))
       exit(1)
 

     #/* ****                               */
     #/* **** Configure logging before app  */
     #/* ****                               */
     dictConfig({
       'version': 1,
       'formatters': {
         'default': {
           'format': '[%(asctime)s] %(levelname)s: %(message)s',
         }
       },
       'handlers': {
         'file': {
           'class': 'logging.FileHandler',
           'level': settings.log_level,
           'formatter': 'default',
           'filename': settings.log_file,
         }
       },
       'root': {
           'level': 'DEBUG',
           'handlers': ['file'],
       }
     })
     logfile = logging.getLogger('file')
     settings.logger = logfile
     logfile.info("Logging to " + str(settings.log_file) + " with " + str(settings.log_level))
     logfile.info("Using configuration " + str(settings.config_path))
     if settings.debug:
       logfile.debug(str(settings))

     @app.errorhandler(apiError)
     def handle_api_error(error):
       response = jsonify(error.to_dict())
       response.status_code = error.status_code
       return response

 
     #/* ****                                 */
     #/* ****  Version Specific API Endpoints */
     #/* ****                                 */
     api = Api(app)
     api.add_resource(jobs,               '/v' + str(settings.version) + '/jobs') 
     api.add_resource(job,                '/v' + str(settings.version) + '/jobs/<id>') 
     api.add_resource(nodes,              '/v' + str(settings.version) + '/nodes') 
     api.add_resource(node,               '/v' + str(settings.version) + '/nodes/<name>') 
     api.add_resource(partitions,         '/v' + str(settings.version) + '/partitions') 
     api.add_resource(reservations,       '/v' + str(settings.version) + '/reservations') 
     if settings.enable_auth:
       api.add_resource(users,            '/v' + str(settings.version) + '/users')
       api.add_resource(user,             '/v' + str(settings.version) + '/users/<name>')


     #/* ****                          */
     #/* ****  Update DB Connection    */
     #/* ****                          */
     if settings.enable_auth:
       app.config['SECRET_KEY'] = settings.key
       app.config['SQLALCHEMY_DATABASE_URI'] = settings.database
       app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
       app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
       db = SQLAlchemy(app)
     

     #/* ****                          */
     #/* ****  API Startup             */
     #/* ****                          */
     if settings.use_ssl:
       app.run( host=settings.host,
                port=settings.port,
                debug=settings.debug, 
                ssl_context=(settings.ssl_cert,settings.ssl_key)
       )
     else:
       app.run( host=settings.host,
                port=settings.port,
                debug=settings.debug, 
       )

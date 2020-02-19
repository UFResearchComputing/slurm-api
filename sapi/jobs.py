#/* ************************************************************************* */
#/* ************************************************************************* */
#/* Description: slurm-api jobs                                               */
#/* Authors:                                                                  */
#/*   - whowell@rc.ufl.edu                                                    */
#/* ************************************************************************* */
#/* ************************************************************************* */
import pyslurm 
import re
import os
import connexion
import six
import sapi
import subprocess
import tempfile
from pwd import getpwnam
from werkzeug.exceptions import Unauthorized

#/* ************************************************************************* */
#/*                                   GET                                     */
#/* ************************************************************************* */
def get(id,limit=100):
    handler = pyslurm.job()
    all_jobs = handler.get()
    try:
      this_job =  handler.find_id(int(id))
    except Exception as e:
      resp = { "code": 500,
               "message": str(e) 
             }
      return resp, 500
    if len(this_job[0].keys()) < 1:
      return connexion.NoContent, 204
    return dict(this_job[0]), 200

#/* ************************************************************************* */
#/*                                  SEARCH                                   */
#/* ************************************************************************* */
def search(limit=100):
    token = sapi.auth.get_token(connexion.request.headers)
    user = sapi.auth.get_user(token)
    uid = getpwnam(user).pw_uid
    jobs = []
    handler = pyslurm.job()
    try:
      user_jobs = handler.find_user(uid)
    except Exception as e:
      resp = { "code": 500,
               "message": str(e) 
             }
      return resp, 500
    if len(user_jobs.values()) < 1:
      return connexion.NoContent, 204
    for this_job in user_jobs.values():
      jobs.append(this_job)
    return jobs[0:limit], 200

#/* ************************************************************************* */
#/*                                 DELETE                                    */
#/* ************************************************************************* */
def delete(id):
    #/* get current sapi settings */
    settings = sapi.configure.configure()
    command = str(settings.scancel)  
    token = sapi.auth.get_token(connexion.request.headers)
    user = sapi.auth.get_user(token)
    uid = getpwnam(user).pw_uid

    #/* get requested job */
    handler = pyslurm.job()
    all_jobs = handler.get()
    try:
      this_job =  handler.find_id(int(id))
    except Exception as e:
      resp = { "code": 500,
               "message": str(e) 
             }
      return resp, 500
    if len(this_job[0].keys()) < 1:
      return 'Not Found', 404

    #/* verify job belongs to this user */
    this_job = this_job[0]
    job_user_id = this_job['user_id']
    if int(uid) != int(job_user_id):
      return "Unauthorized", 401

    #/* cancel the job */
    command = command + ' ' + str(id)
    try:
      cancel_response = subprocess.check_output(command.split())
    except Exception as e:
      resp = { "code": 500,
               "message": "Failure cancelling job " + str(id) +
                        ": " + str(e) 
             }
      return resp, 500

    #/* clean return no content */
    return connexion.NoContent, 204
    

#/* ************************************************************************* */
#/*                                  POST                                     */
#/* ************************************************************************* */
def post(body):
    #/* get current sapi settings */
    settings = sapi.configure.configure()
    command = str(settings.sbatch)  
    token = sapi.auth.get_token(connexion.request.headers)
    user = sapi.auth.get_user(token)

    #/* process translations from our api to pyslurm fields */
    job_spec = {}
    tmp_script = False
    if "account" in body:
      job_spec['account'] = body['account']
    if "chdir" in body:
      job_spec['work_dir'] = body['chdir']
    if "constraint" in body:
      job_spec['constraint'] = body['constraint']
    if "cpus_per_task" in body:
      job_spec['cpus-per-task'] = body['cpus_per_task']
    if "error" in body:
      job_spec['error'] = body['error']
    if "mail_type" in body:
      job_spec['mail-type'] = body['mail_type']
    if "mail_user" in body:
      job_spec['mail-user'] = body['mail_user']
    if "mem_per_cpu" in body:
      job_spec['mem-per-cpu'] = body['mem_per_cpu']
    if "name" in body:
      job_spec['job-name'] = body['name']
    if "nodelist" in body:
      job_spec['nodelist'] = body['nodelist']
    if "ntasks" in body:
      job_spec['ntasks'] = body['ntasks']
    if "output" in body:
      job_spec['output'] = body['output']
    if "partition" in body:
      job_spec['partition'] = body['partition']
    if "qos" in body:
      job_spec['qos'] = body['qos']
    if "reservation" in body:
      job_spec['reservation'] = body['reservation']
    if "exclusive" in body:
      if body['exclusive'] == True:
        job_spec['exclusive'] = True 
    if "ticrypt" in body:
      if body['ticrypt'] == True:
        job_spec['ticrypt'] = True 
    if "time" in body:
      job_spec['time'] = body['time']
    if not "uid" in body:
      try:
        job_spec['uid'] = getpwnam(user).pw_uid 
      except Exception as e:
        resp = { "code": 500,
                 "message": "failure resolving user uid: " + str(e) 
               }
        return resp, 500
    if not "gid" in body:
      try:
        job_spec['gid'] = getpwnam(user).pw_gid 
      except Exception as e:
        resp = { "code": 500,
                 "message": "failure resolving user gid: " + str(e) 
               }
        return resp, 500
    if "wrap" in body:
      job_spec['wrap'] = body['wrap']
      tmp_script = True
    elif "script" in body:
      job_spec['script'] = body['script']

    #/* work around for error where chdir does not apply to work_dir */
    original_dir = os.getcwd()
    if "chdir" in job_spec:
      os.chdir(job_spec['chdir'])
    else:
      os.chdir(settings.tmp)

    #/* if wrap used, we need to form a script since not using pyslurm yet */
    if tmp_script == True:
      #/* open a tempfile for batch script */
      tempfile.tempdir = settings.tmp
      try:
        tmp_script = tempfile.NamedTemporaryFile(
                             prefix="sapi-wrap_",
                             suffix=".sh",
                             mode='w+t',
                             delete=False )
      except Exception as e:
        os.chdir(original_dir)
        resp = { "code": 500,
                 "message": "Failure opening temporary batch script: " + str(e) 
               }
        return resp, 500
      #/* write shebang if missing */
      if not re.match("^#!/bin/bash",job_spec['wrap']):
        try:
          tmp_script.writelines('#!/bin/bash' + "\n")
        except Exception as e:
          os.chdir(original_dir)
          resp = { "code": 500,
                   "message": "Failure adding shebang to temporary job script: " + str(e) 
                 }
          return resp, 500
      #/* write out wrap lines to temporary script */
      try:
        tmp_script.writelines(job_spec['wrap'] + "\n")
      except Exception as e:
        os.chdir(original_dir)
        resp = { "code": 500,
                 "message": "Failure writing wrapped lines to temporary script: " + str(e) 
               }
        return resp, 500
      #/* set ownership and mode */
      try:
        os.chown(tmp_script.name,job_spec['uid'],job_spec['gid'])
        os.chmod(tmp_script.name, 0o640)
      except Exception as e:
        resp = { "code": 500,
                 "message": "Failure setting ownership of temporary script: " + str(e) 
               }
        return resp, 500
    if tmp_script:
      tmp_script.close()
      job_spec['script'] = str(tmp_script.name)
    
    #/* submit job via system sbatch */
    #/*   this is present only until pyslurm has updates to job submit */
    for option in job_spec.keys():
      if not re.match("script",option) and not re.match("wrap",option):
        if type(job_spec[option]) == type(True):
          if job_spec[option] == True:
            command = command + ' --' + str(option)
        else:
          command = command + ' --' + str(option) + '=' + str(job_spec[option])
    command = command + ' ' + str(job_spec['script'])
 
    try:
      submission_response = subprocess.check_output(command.split())
    except Exception as e:
      resp = { "code": 500,
               "message": "Failure in submission of batch script " + str(job_spec['script']) +
                        ": " + str(e) 
             }
      return resp, 500

    #/* parse out jobid in order to lookup and return initial job data */
    job_id = False
    for line in submission_response.decode().split("\n"):
      if re.match("Submitted batch job \d+",line):
        job_id = int(line.split()[-1])


    #/* get back the job as a JobResult from pyslurm */
    handler = pyslurm.job()
    try:
      all_jobs = handler.get()
    except Exception as e:
      os.chdir(original_dir)
      resp = { "code": 500,
               "message": "failure initializing job list after job submission: " + str(e)
             }
      return resp, 500
    try:
      this_job = handler.find_id(int(job_id))
    except Exception as e:
      os.chdir(original_dir)
      resp = { "code": 500,
               "message": "failure looking up job after submission: " + str(e)
             }
      return resp, 500  

    os.chdir(original_dir)
    return dict(this_job[0]), 200

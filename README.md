# Warning
* This branch is a POC to allow first pass initial testing. 
* A formal first release will be developed in a 1.0 branch.
* As such **NOTHING IN THIS BRANCH SHOULD BE USED FOR PERMANENT REFERENCE OR DEVELOPMENT**
* v1.0 will coordinated against pyslurm api v2 or worked around v1 in order to reference objects and fields in the syntax common to scontrol, srun, and sbatch

# Overview
Provides a python flask RESTful API for SLURM

## Notes

* node running the API must have the slurm libraries installed and be able to resolve user names (for example an LDAP client)

* pyslurm of appropriate version compatibility must be build referencing slurm paths if they are non-standard

* job submission requires the API be run as root to allow su to users for submission, or the API must run as user in slurm who is allowed to submit jobs for other users

* configuration options reside in a slurm-virt.ini config file. By default this is located at /etc/slurm-api.ini, but can be changed via the environment variable SLURM_API_CONFIG


## UFRC Installation 
* ** only valid in Library lifecycle environment **
* dependencies have been built and published for python36-* 
* slurm-api is not RPM packaged yet due to waiting on v1.0
  - clone repo on target node
  - yum install the python36 dependencies
  - generate the sqlite auth database using referenced schema in conf/
  - setup /etc/slurm-api.ini based on the example configuration and referencing the sqlite database
  - run it from src/


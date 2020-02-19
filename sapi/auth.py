#/* ************************************************************************* */
#/* ************************************************************************* */
#/* Description: slurm-api jwt token methods                                  */
#/* Authors:                                                                  */
#/*   - whowell@rc.ufl.edu                                                    */
#/* ************************************************************************* */
#/* ************************************************************************* */
import time
import jwt
import six
import re
from sapi.configure import configure
from werkzeug.exceptions import Unauthorized


#/* ************************************************************************* */
#/*                            JWT PARAMETERS                                 */
#/* ************************************************************************* */
#/* !!!! move these to config and load from config methods !!!!               */
try:
  settings = configure()
except Exception as e:
  print("Configuration Error: " + str(e))
  exit(1)
JWT_ISSUER = settings.issuer
JWT_SECRET = settings.secret
JWT_LIFETIME_SECONDS = settings.lifetime
JWT_ALGORITHM = settings.algorithm

#/* ************************************************************************* */
#/*                    method to return user from token                       */
#/* ************************************************************************* */
def get_user(token):
  try:
    token_info = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
  except Exception as e:
    six.raise_from(Unauthorized, e)
  if not re.match(JWT_ISSUER,token_info['iss']):
    six.raise_from(Unauthorized, e)
  elif int(time.time()) >= token_info['exp']:
    six.raise_from(Unauthorized, e)
  else:
    return token_info['sub']

#/* ************************************************************************* */
#/*                     method to get token from header                       */
#/* ************************************************************************* */
def get_token(headers):
  try:
    bearer = headers['Authorization']
    bearer = bearer.split(' ')
    token = bearer[1]
  except Exception as e:
    six.raise_from(Unauthorized,e )
  return token

#/* ************************************************************************* */
#/*                        method to decode a token                           */
#/* ************************************************************************* */
def decode_token(token):
  try:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
  except Exception as e:
    six.raise_from(Unauthorized, e)
  
#/* ************************************************************************* */
#/*                      method to generate a token                           */
#/* ************************************************************************* */
def generate_token(user):
  timestamp = int(time.time())
  payload = {
    "iss": JWT_ISSUER,
    "iat": int(timestamp),
    "exp": int(timestamp) + int(JWT_LIFETIME_SECONDS),
    "sub": str(user),
  }

  return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

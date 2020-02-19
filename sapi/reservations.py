#/* ************************************************************************* */
#/* ************************************************************************* */
#/* Description: slurm-api reservations                                       */
#/* Authors:                                                                  */
#/*   - whowell@rc.ufl.edu                                                    */
#/* ************************************************************************* */
#/* ************************************************************************* */
import pyslurm 
import re
from connexion import NoContent

#/* ************************************************************************* */
#/*                                   GET                                     */
#/* ************************************************************************* */
def get(id,limit=100):
    handler = pyslurm.reservation()
    all_reservations = handler.get()
    try:
      reservation =  handler.find_id(str(id))
    except Exception as e:
      resp = { "code": 500,
               "message": str(e) 
             }
      return resp, 500
    if len(reservation.keys()) < 1:
      return NoContent, 204
    reservation['name'] = str(id)
    return dict(reservation), 200

#/* ************************************************************************* */
#/*                                  SEARCH                                   */
#/* ************************************************************************* */
def search(limit=100):
    reservations = []
    handler = pyslurm.reservation()
    try:
      all_reservations = handler.get()
    except Exception as e:
      resp = { "code": 500,
               "message": str(e) 
             }
      return resp, 500
    if len(all_reservations.values()) < 1:
      return NoContent, 204
    for this_res_name in all_reservations.keys():
      all_reservations[str(this_res_name)]['name'] = str(this_res_name)
      reservations.append(all_reservations[str(this_res_name)])
    return reservations[0:limit], 200

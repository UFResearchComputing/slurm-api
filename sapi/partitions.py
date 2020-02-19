#/* ************************************************************************* */
#/* ************************************************************************* */
#/* Description: slurm-api partitions                                         */
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
    handler = pyslurm.partition()
    try:
      all_partitions =  handler.get()
    except Exception as e:
      resp = { "code": 500,
               "message": str(e) 
             }
      return resp, 500
    all_partitions = dict(all_partitions)
    if len(all_partitions.values()) < 1:
      return NoContent, 204
    for this_part in all_partitions.values():
      if re.match(str(id),this_part['name']):
        return dict(this_part), 200

    return NoContent, 204

#/* ************************************************************************* */
#/*                                  SEARCH                                   */
#/* ************************************************************************* */
def search(limit=100):
    partitions = []
    handler = pyslurm.partition()
    try:
      all_partitions = handler.get()
    except Exception as e:
      resp = { "code": 500,
               "message": str(e) 
             }
      return resp, 500
    if len(all_partitions.values()) < 1:
      return NoContent, 204
    for this_part in all_partitions.values():
      partitions.append(this_part)
    return partitions[0:limit], 200

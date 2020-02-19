#/* ************************************************************************* */
#/* ************************************************************************* */
#/* Description: slurm-api nodes                                              */
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
    node_o = pyslurm.node()
    try:
      this_node =  node_o.get_node(str(id))
    except Exception as e:
      resp = { "code": 500,
               "message": str(e) 
             }
      return resp, 500
    if len(this_node.values()) < 1:
      return NoContent, 204
    return dict(this_node[str(id)]), 200

#/* ************************************************************************* */
#/*                                  SEARCH                                   */
#/* ************************************************************************* */
def search(limit=100):
    nodes = []
    node_o = pyslurm.node()
    try:
      all_nodes = node_o.get()
    except Exception as e:
      resp = { "code": 500,
               "message": str(e) 
             }
      return resp, 500
    if len(all_nodes.values()) < 1:
      return NoContent, 204
    for node in all_nodes.values():
      nodes.append(node)
    return nodes[0:limit], 200

import zlab

node_coordinate_set = [[0.0, 0.0, 0.0], [3.0, 0.0, 0.0], [0.0, 4.0, 0.0], [3.0, 2.0, 0.0],
                        [0.0, 0.0, 2.0], [3.0, 0.0, 2.0], [0.0, 4.0, 2.0], [3.0, 2.0, 2.0],
                        [5.0, 0.0, 0.0], [5.0, 2.0, 0.0], [5.0, 0.0, 2.0], [5.0, 2.0, 2.0]]

element_set_3d = [[1, 2, 3, 4, 5, 6, 7, 8],
               [2, 9, 4, 10, 6, 11, 8, 12]]

element_set_2d = [[1, 2, 3, 4],
               [5, 6, 7, 8],
               [2, 9, 4, 10],
               [6, 11, 8, 12]]

element_set_1d = [[1, 2],
               [3, 4],
               [5, 6],
               [7, 8],
               [2, 9],
               [4, 10],
               [6, 11],
               [8, 12]]

    
 
#zlab.data_points(node_coordinate_set)
#zlab.nodes(node_coordinate_set)
# this will give an error because the 'nodes' nodeset of the field 'coordinates' already exists
#zlab.linear_mesh(node_coordinate_set, element_set_1d)
#zlab.linear_mesh(node_coordinate_set, element_set_2d)
zlab.linear_mesh(node_coordinate_set, element_set_3d)
zlab.show()
import time
time.sleep(10)
zlab.hide()

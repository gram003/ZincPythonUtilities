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

    
 
#zlab.data_points(node_coordinate_set, datapoints_size=0.13, datapoints_number=True)
#zlab.nodes(node_coordinate_set, nodes_size=0.1, nodes_number=True)
# this will give an error because the 'nodes' nodeset of the field 'coordinates' already exists
zlab.linear_mesh(node_coordinate_set, element_set_1d, nodes_size=0.2, nodes_number=True)
#zlab.linear_mesh(node_coordinate_set, element_set_2d)
#zlab.linear_mesh(node_coordinate_set, element_set_3d, nodes_size=0.1, nodes_number=True)
zlab.show()
# import time
# time.sleep(10)
# zlab.hide()

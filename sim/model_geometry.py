"""Geometry utilities for offline placement; no dependency on CAD libraries."""
import itertools
import numpy as np
import mujoco


def geom_vertices_world(model, data, geom_id):
    kind = model.geom_type[geom_id]
    if kind == mujoco.mjtGeom.mjGEOM_MESH:
        mesh = model.geom_dataid[geom_id]
        start, count = model.mesh_vertadr[mesh], model.mesh_vertnum[mesh]
        points = model.mesh_vert[start:start+count]
    elif kind == mujoco.mjtGeom.mjGEOM_BOX:
        points = np.array(list(itertools.product((-1,1), repeat=3))) * model.geom_size[geom_id]
    else:
        raise ValueError(f'Unsupported robot collision shape {kind}; add its support points.')
    return points @ data.geom_xmat[geom_id].reshape(3,3).T + data.geom_xpos[geom_id]


def neutral_collision_vertices(model):
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    root = model.body('base').id
    points = [geom_vertices_world(model, data, i) - data.xpos[root]
              for i in range(model.ngeom)
              if model.geom_bodyid[i] != 0 and model.geom_contype[i] != 0]
    return np.concatenate(points)


def place_neutral_robot(model, data, tilt, azimuth, clearance=.002, support_points=None):
    """Place the neutral robot just above the floor in any base orientation."""
    quat = np.array([np.cos(tilt/2), np.sin(tilt/2)*np.cos(azimuth), np.sin(tilt/2)*np.sin(azimuth), 0])
    rotation = np.empty(9)
    mujoco.mju_quat2Mat(rotation, quat)
    if support_points is None:
        support_points = neutral_collision_vertices(model)
    lowest_z = np.min(support_points @ rotation.reshape(3,3)[2])
    data.qpos[:3] = [0, 0, clearance-lowest_z]
    data.qpos[3:7] = quat
    data.qpos[-2:] = 0
    mujoco.mj_forward(model, data)

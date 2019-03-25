import IPython
from ipywidgets import IntSlider, interact, widgets
from k3d.helpers import minmax
from k3d_vtk.reader import read_vtkfile
from k3d.plot import Plot as k3dPlot
import k3d
from vtk.util import numpy_support
import numpy as np
import vtk
from matplotlib.cm import get_cmap
from matplotlib.colors import Colormap

def _transform_to_k3d(timestep, poly_data, color_attribute_name):
    '''
    this function mirrors the prepartion in k3d.vtk_poly_data
    :param timestep: attribute from vtk collection file
    :param poly_data: vtk reader Output for one single vtk file
    :param color_attribute_name: Determines mesh colorization, 3-Tuple of Vtk Dataset name, min value, max value
    :return: 5-Tuple to match necessary updates to mesh when advancing the timestep
    '''
    if poly_data.GetPolys().GetMaxCellSize() > 3:
        cut_triangles = vtk.vtkTriangleFilter()
        cut_triangles.SetInputData(poly_data)
        cut_triangles.Update()
        poly_data = cut_triangles.GetOutput()

    if color_attribute_name is not None:
        attribute = numpy_support.vtk_to_numpy(poly_data.GetPointData().GetArray(color_attribute_name))
        color_range = minmax(attribute)
    else:
        attribute = []
        color_range = [0,-1,]#[-np.inf, np.inf]
    vertices = numpy_support.vtk_to_numpy(poly_data.GetPoints().GetData())
    indices = numpy_support.vtk_to_numpy(poly_data.GetPolys().GetData()).reshape(-1, 4)[:, 1:4]

    return timestep, np.array(attribute, np.float32), color_range[0], color_range[1], \
        np.array(vertices, np.float32), np.array(indices, np.uint32)


def _add_colorbar(vtkplot, bounds, v_minmax, color_map):
    z = (bounds[2] + bounds[5]) / 2
    gap = 0.1
    width = np.array([gap * np.abs(bounds[0]-bounds[3]), 0, 0])
    grid_top_left = np.array([bounds[0] - gap, bounds[4], z])
    grid_bottom_left = np.array([bounds[0] - gap, bounds[1], z])
    vertices = [grid_top_left, grid_bottom_left, grid_bottom_left - width, grid_top_left - width]
    indices = [[0, 3, 2], [1, 2, 0]]
    vertex_attribute = [v_minmax[1], v_minmax[0], v_minmax[0], v_minmax[1]]
    vtkplot += k3d.mesh(vertices, indices, attribute=vertex_attribute,
                        color_map=color_map, color_range=v_minmax)
    top = grid_top_left +    np.array([0, -0.2*gap, 0]) - 1.1 * width
    bot = grid_bottom_left + np.array([0,  0.2*gap, 0]) - 1.1 * width
    vtkplot += k3d.text(text=f'Max: {np.round(v_minmax[1])}', position=top, color=0, reference_point='rc')
    vtkplot += k3d.text(text=f'Min: {np.round(v_minmax[0])}', position=bot, color=0, reference_point='rc')


class VTKPlot(k3dPlot):
    def __init__(self, vtk_data, color_attribute_name='Data',
                 color_map=k3d.basic_color_maps.CoolWarm,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.idx = 0

        if 'transform' in kwargs.keys() and len(vtk_data) > 1:
            raise RuntimeError('supplying transforms is currently not supported for teim series VTK Data')

        self.vtk_data = np.stack([_transform_to_k3d(v[0], v[1], color_attribute_name) for v in vtk_data])
        self.value_minmax = (np.nanmin(self.vtk_data[:, 2]), np.nanmax(self.vtk_data[:, 3]))
        self.mesh = k3d.vtk_poly_data(vtk_data[0][1], color_attribute=(color_attribute_name, *self.value_minmax),
                                      color_map=color_map)
        self.timestep = vtk_data[0][0]
        self += self.mesh

    def _goto_idx(self, idx):
        if not (0<= self.idx < len(self.vtk_data)):
            raise RuntimeWarning(f'Index {idx} outside data range for VTKPlot')
            return
        self.idx = idx
        self.timestep, self.mesh.attribute, _, _, \
            self.mesh.vertices, self.mesh.indices = self.vtk_data[self.idx]

    def dec(self):
        self._goto_idx(self.idx-1)

    def inc(self):
        self._goto_idx(self.idx+1)


def plot(vtkfile_path, color_attribute_name, color_map=get_cmap('viridis')):
    ''' Generate a k3d Plot and associated controls for VTK data from file

    :param vtkfile_path: the path to load vtk data from. Can be a single .vtu or a collection
    :param color_attribute_name: which data array from vtk to use for plot coloring
    :param color_map: a Matplotlib Colormap object or a K3D array((step, r, g, b))
    :return: the generated Plot object
    '''
    if isinstance(color_map, Colormap):
        color_map = [(x, *color_map(x)[:3]) for x in np.linspace(0, 1, 256)]

    data = read_vtkfile(vtkfile_path)
    size = len(data)

    # getbounds: (xmin, xmax, ymin, ymax, zmin, zmax)
    all_bounds = np.stack([p[1].GetBounds() for p in data])
    combined_bounds = np.array([np.min(all_bounds[:, 0]),
                                np.min(all_bounds[:, 2]),
                                np.min(all_bounds[:, 4]),
                                np.max(all_bounds[:, 1]),
                                np.max(all_bounds[:, 3]),
                                np.max(all_bounds[:, 5])])
    # guesstimate
    fov_angle = 30
    absx = np.abs(combined_bounds[0] - combined_bounds[3])
    # camera[posx, posy, posz, targetx, targety, targetz, upx, upy, upz]
    c_dist = np.sin((90 - fov_angle) * np.pi / 180) * absx / (2 * np.sin(fov_angle * np.pi / 180))

    vtkplot = VTKPlot(data, color_attribute_name=color_attribute_name,  grid_auto_fit=False,
                      camera_auto_fit=False, color_map=color_map)
    # display needs to have been called before chaning camera
    vtkplot.display()
    vtkplot.grid = combined_bounds
    xhalf = (combined_bounds[0] + combined_bounds[3]) / 2
    yhalf = (combined_bounds[1] + combined_bounds[4]) / 2
    zhalf = (combined_bounds[2] + combined_bounds[5]) / 2
    vtkplot.camera = (xhalf, yhalf, zhalf + c_dist,
                      xhalf, yhalf, zhalf,
                      0, 1, 0)
    _add_colorbar(vtkplot, combined_bounds, vtkplot.value_minmax, color_map)
    if size > 1:
        ws = interact(idx=IntSlider(min=0, max=size-1, step=1, value=0, description='Timestep:')).widget(vtkplot._goto_idx)
        IPython.display.display(ws)
    return vtkplot
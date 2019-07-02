# coding=utf-8
import numpy as np
import os, os.path, json, inspect, shutil, six, re
from os.path import join, isfile, isdir

from phi.math import Struct


def read_zipped_array(filename):
    file = np.load(filename)
    array = file[file.files[-1]] # last entry in npz file has to be data array
    if array.shape[0] != 1:
        array = array.reshape((1,)+array.shape)
    if array.shape[-1] != 1:
        array = array[...,::-1]
    return array


def write_zipped_array(filename, array):
    if array.shape[0] == 1:
        array = array[0,...]
    if array.shape[-1] != 1:
        array = array[...,::-1]
    np.savez_compressed(filename, array)


def _check_same_dimensions(arrays):
    for array in arrays:
        if array.shape[1:-1] != arrays[0].shape[1:-1]:
            raise ValueError("All arrays should have the same spatial dimensions, but got %s and %s" % (array.shape, arrays[0].shape))


def read_sim_frame(simpath, fieldnames, frame, set_missing_to_none=True):
    if isinstance(fieldnames, six.string_types): fieldnames = [fieldnames]
    for fieldname in fieldnames:
        filename = join(simpath, "%s_%06i.npz" % (fieldname, frame))
        if os.path.isfile(filename):
            yield read_zipped_array(filename)
        else:
            if set_missing_to_none:
                yield None
            else:
                raise IOError("Missing frame at frame %d: %s" % (frame, filename))


def write_sim_frame(simpath, arrays, fieldnames, frame, check_same_dimensions=False):
    if check_same_dimensions: _check_same_dimensions(arrays)
    os.path.isdir(simpath) or os.mkdir(simpath)
    if not isinstance(fieldnames, (tuple, list)) and not isinstance(arrays, (tuple, list)):
        fieldnames = [fieldnames]
        arrays = [arrays]
    filenames = [join(simpath, "%s_%06i.npz" % (name, frame)) for name in fieldnames]
    for i in range(len(arrays)):
        write_zipped_array(filenames[i], arrays[i])
    return filenames


def read_sim_frames(simpath, fieldnames=None, frames=None):
    if fieldnames is None: fieldnames = get_fieldnames(simpath)
    if not fieldnames: return []
    if frames is None: frames = get_frames(simpath, fieldnames[0])
    if isinstance(frames, int): frames = [frames]
    single_fieldname = isinstance(fieldnames, six.string_types)
    if single_fieldname: fieldnames = [fieldnames]

    field_lists = [[] for f in fieldnames]
    for i in frames:
        fields = read_sim_frame(simpath, fieldnames, i, set_missing_to_none=False)
        for j in range(len(fieldnames)):
            field_lists[j].append(fields[j])
    result = [np.concatenate(list, 0) for list in field_lists]
    return result if not single_fieldname else result[0]


def get_fieldnames(simpath):
    fieldnames_set = {f[:-11] for f in os.listdir(simpath) if f.endswith(".npz")}
    return sorted(fieldnames_set)


def first_frame(simpath, fieldname=None):
    return min(get_frames(simpath, fieldname))


def get_frames(simpath, fieldname=None, mode="intersect"):
    if fieldname is not None:
        all_frames = {int(f[-10:-4]) for f in os.listdir(simpath) if f.startswith(fieldname) and f.endswith(".npz")}
        return sorted(all_frames)
    else:
        frames_lists = [get_frames(simpath, fieldname) for fieldname in get_fieldnames(simpath)]
        if mode.lower() == "intersect":
            intersection = set(frames_lists[0]).intersection(*frames_lists[1:])
            return sorted(intersection)
        elif mode.lower() == "union":
            if not frames_lists:
                return []
            union = set(frames_lists[0]).union(*frames_lists[1:])
            return sorted(union)


class Scene(object):

    def __init__(self, dir, category, index):
        self.dir = dir
        self.category = category
        self.index = index
        self._properties = None

    @property
    def path(self):
        return join(self.dir, self.category, "sim_%06d"%self.index)

    def subpath(self, name, create=False):
        path = join(self.path, name)
        if create and not os.path.isdir(path):
            os.mkdir(path)
        return path

    def _init_properties(self):
        if self._properties is not None: return
        dfile = join(self.path, "description.json")
        if isfile(dfile):
            self._properties = json.load(dfile)
        else:
            self._properties = {}

    def exists_config(self):
        return isfile(join(self.path, "description.json"))


    @property
    def properties(self):
        self._init_properties()
        return self._properties

    @properties.setter
    def properties(self, dict):
        self._properties = dict
        with open(join(self.path, "description.json"), "w") as out:
            json.dump(self._properties, out, indent=2)

    def put_property(self, key, value):
        self._init_properties()
        self._properties[key] = value
        with open(join(self.path, "description.json"), "w") as out:
            json.dump(self._properties, out, indent=2)

    def read_sim_frames(self, fieldnames=None, frames=None):
        return read_sim_frames(self.path, fieldnames=fieldnames, frames=frames)

    def read_array(self, fieldname, frame):
        return next(read_sim_frame(self.path, [fieldname], frame, set_missing_to_none=False))

    def write_sim_frame(self, arrays, fieldnames, frame, check_same_dimensions=False):
        write_sim_frame(self.path, arrays, fieldnames, frame, check_same_dimensions=check_same_dimensions)

    def write(self, struct, names=None, frame=0):
        if Struct.isstruct(struct):
            if names is None:
                names = Struct.mapnames(struct)
            values, _ = Struct.flatten(struct)
            names, _ = Struct.flatten(names)
            names = [self._filename(name) for name in names]
            self.write_sim_frame(values, names, frame)
        else:
            name = str(names) if names is not None else 'unnamed'
            self.write_sim_frame(struct, name, frame)

    def read(self, struct, frame=0):
        if Struct.isstruct(struct):
            names = Struct.flatten(struct)
            if not np.all([isinstance(n, six.string_types) for n in names]):
                struct = Struct.mapnames(struct)
            return Struct.flatmap(lambda name: self.read_array(self._filename(name), frame), struct)
        else:
            return self.read_array('unnamed', frame)

    def _filename(self, structname):
        structname = structname.replace('._', '.').replace('.', '_')
        if structname.startswith('_'): structname = structname[1:]
        return structname

    @property
    def fieldnames(self):
        return get_fieldnames(self.path)

    @property
    def frames(self):
        return get_frames(self.path)

    def get_frames(self, mode="intersect"):
        return get_frames(self.path, None, mode)

    def __str__(self):
        return self.path

    def __repr__(self):
        return self.path

    def copy_calling_script(self):
        script_path = inspect.stack()[1][1]
        script_name = os.path.basename(script_path)
        src_path = os.path.join(self.path, "src")
        os.path.isdir(src_path) or os.mkdir(src_path)
        target = os.path.join(self.path, "src", script_name)
        shutil.copy(script_path, target)
        try:
            shutil.copystat(script_path, target)
        except:
            pass # print("Could not copy file metadata to %s"%target)

    def copy_src(self, path):
        file_name = os.path.basename(path)
        src_dir = os.path.dirname(path)
        target_dir = join(self.path, "src")
        # Create directory and copy
        isdir(target_dir) or os.mkdir(target_dir)
        shutil.copy(path, join(target_dir, file_name))
        try:
            shutil.copystat(path, join(target_dir, file_name))
        except:
            pass  # print("Could not copy file metadata to %s"%target)

    def mkdir(self, subdir=None):
        path = self.path
        isdir(path) or os.mkdir(path)
        if subdir is not None:
            subpath = join(path, subdir)
            isdir(subpath) or os.mkdir(subpath)

    def remove(self):
        if isdir(self.path):
            shutil.rmtree(self.path)

    @staticmethod
    def create(directory, category=None, count=1, mkdir=True, copy_calling_script=True):
        if count > 1:
            return SceneBatch([Scene.create(directory, category, 1, mkdir, copy_calling_script) for i in range(count)])
        # Single scene
        directory = os.path.expanduser(directory)
        if category is None:
            category = os.path.basename(directory)
            directory = os.path.dirname(directory)
        else:
            category = slugify(category)

        scenedir = join(directory, category)
        if not isdir(scenedir):
            os.makedirs(scenedir)
            next_index = 0
        else:
            indices = [int(name[4:]) for name in os.listdir(scenedir) if name.startswith("sim_")]
            if not indices:
                next_index = 0
            else:
                next_index = max(indices) + 1
        scene = Scene(directory, category, next_index)
        if mkdir: scene.mkdir()
        if copy_calling_script:
            assert mkdir
            scene.copy_calling_script()
        return scene

    @staticmethod
    def list(directory, category=None, indexfilter=None, max_count=None):
        directory = os.path.expanduser(directory)
        if not category:
            root_path = directory
            category = os.path.basename(directory)
            directory = os.path.dirname(directory)
        else:
            root_path = join(directory, category)
        if not os.path.isdir(root_path): return []
        indices = [int(sim[4:]) for sim in os.listdir(root_path) if sim.startswith("sim_")]
        if indexfilter:
            indices = [i for i in indices if indexfilter(i)]
        if max_count and len(indices) >=  max_count:
            indices = indices[0:max_count]
        return [Scene(directory, category, scene_index) for scene_index in indices]

    @staticmethod
    def at(sim_dir):
        sim_dir = os.path.expanduser(sim_dir)
        dirname = os.path.basename(sim_dir)
        if not dirname.startswith("sim_"):
            raise ValueError("%s is not a valid scene directory."%sim_dir)
        category_directory = os.path.dirname(sim_dir)
        category = os.path.basename(category_directory)
        directory = os.path.dirname(category_directory)
        index = int(dirname[4:])
        return Scene(directory, category, index)


class SceneBatch(Scene):

    def __init__(self, scenes):
        Scene.__init__(self, scenes[0].dir, scenes[0].category, scenes[0].index)
        self.scenes = scenes

    @property
    def batch_size(self):
        return len(self.scenes)

    def write_sim_frame(self, arrays, fieldnames, frame, check_same_dimensions=False):
        for array in arrays:
            assert array.shape[0] == len(self.scenes)
        for i,scene in enumerate(self.scenes):
            array_slices = [array[i,...] for array in arrays]
            scene.write_sim_frame(array_slices, fieldnames, frame=frame, check_same_dimensions=check_same_dimensions)

    def read_sim_frames(self, fieldnames=None, frames=None):
        raise NotImplementedError()

    def read_array(self, fieldname, frame):
        return np.concatenate([scene.read_array(fieldname, frame) for scene in self.scenes])




def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.
    """
    for greek_letter, name in greek.items():
        value = value.replace(greek_letter, name)
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    value = re.sub('[-\s]+', '-', value)
    return value


greek = {
    u'Α': 'Alpha',      u'α': 'alpha',
    u'Β': 'Beta',       u'β': 'beta',
    u'Γ': 'Gamma',      u'γ': 'gamma',
    u'Δ': 'Delta',      u'δ': 'delta',
    u'Ε': 'Epsilon',    u'ε': 'epsilon',
    u'Ζ': 'Zeta',       u'ζ': 'zeta',
    u'Η': 'Eta',        u'η': 'eta',
    u'Θ': 'Theta',      u'θ': 'theta',
    u'Ι': 'Iota',       u'ι': 'iota',
    u'Κ': 'Kappa',      u'κ': 'kappa',
    u'Λ': 'Lambda',     u'λ': 'lambda',
    u'Μ': 'Mu',         u'μ': 'mu',
    u'Ν': 'Nu',         u'ν': 'nu',
    u'Ξ': 'Xi',         u'ξ': 'xi',
    u'Ο': 'Omicron',    u'ο': 'omicron',
    u'Π': 'Pi',         u'π': 'pi',
    u'Ρ': 'Rho',        u'ρ': 'rho',
    u'Σ': 'Sigma',      u'σ': 'sigma',
    u'Τ': 'Tau',        u'τ': 'tau',
    u'Υ': 'Upsilon',    u'υ': 'upsilon',
    u'Φ': 'Phi',        u'φ': 'phi',
    u'Χ': 'Chi',        u'χ': 'chi',
    u'Ψ': 'Psi',        u'ψ': 'psi',
    u'Ω': 'Omega',      u'ω': 'omega',
}
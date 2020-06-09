from hypothesis import strategies as hyst
from hypothesis import assume, settings, HealthCheck
from hypothesis.extra import numpy as hynp
import numpy as np
import pytest

from pymor.core.config import config
from pymor.vectorarrays.list import NumpyListVectorSpace
from pymor.vectorarrays.block import BlockVectorSpace
from pymor.vectorarrays.numpy import NumpyVectorSpace
if config.HAVE_FENICS:
    import dolfin as df
    from pymor.bindings.fenics import FenicsVectorSpace

if config.HAVE_DEALII:
    from pydealii.pymor.vectorarray import DealIIVectorSpace

if config.HAVE_NGSOLVE:
    import ngsolve as ngs
    import netgen.meshing as ngmsh
    from netgen.geom2d import unit_square
    from pymor.bindings.ngsolve import NGSolveVectorSpace

    NGSOLVE_spaces = {}

    def create_ngsolve_space(dim):
        if dim not in NGSOLVE_spaces:
            mesh = ngmsh.Mesh(dim=1)
            if dim > 0:
                pids = []
                for i in range(dim + 1):
                    pids.append(mesh.Add(ngmsh.MeshPoint(ngmsh.Pnt(i / dim, 0, 0))))
                for i in range(dim):
                    mesh.Add(ngmsh.Element1D([pids[i], pids[i + 1]], index=1))
            NGSOLVE_spaces[dim] = NGSolveVectorSpace(ngs.L2(ngs.Mesh(mesh), order=0))
        return NGSOLVE_spaces[dim]

MAX_LENGTH = 102
hy_lengths = hyst.integers(min_value=0, max_value=MAX_LENGTH)
hy_float_array_elements = hyst.floats(allow_nan=False, allow_infinity=False, min_value=-1, max_value=1)
hy_complex_array_elements = hyst.complex_numbers(allow_nan=False, allow_infinity=False, max_magnitude=2)
# TODO non-fixed sampling pool
hy_block_space_dims = hyst.sampled_from([(32, 1), (0, 3), (0, 0), (10,), (34, 1), (32, 3, 1), (1, 1, 1)])
hy_block_space_dims_incompat = hyst.sampled_from(list(zip([(3, 2), (9,), (34, 1, 1), (32, 3, 3), (3, 3, 3)],  # dim1
[(3, 1), (9, 3), (34, 2, 1), (32, 3), (4, 3, 3)])))

hy_reserves = hyst.integers(min_value=0, max_value=3)
hy_dtypes = hyst.sampled_from([np.float64, np.complex128])


def _vector_array_from_empty_reserve(v, reserve):
    if reserve == 0:
        return v
    if reserve == 1:
        r = 0
    elif reserve == 2:
        r = len(v) + 10
    elif reserve == 3:
        r = int(len(v) / 2)
    c = v.empty(reserve=r)
    c.append(v)
    return c


@hyst.composite
def hy_dims(draw, count, compatible):
    dims = hyst.integers(min_value=0, max_value=34)
    if compatible:
        return draw(equal_tuples(dims, count))
    dim_tuple = draw(hyst.tuples(*[dims for _ in range(count)]))
    for d in range(1,count):
        assume(dim_tuple[d] != dim_tuple[0])
    return dim_tuple


def nothing(*args, **kwargs):
    return hyst.nothing()


def np_arrays(length, dim, dtype=None):
    if dtype is None:
        return hynp.arrays(dtype=np.float64, shape=(length, dim), elements=hy_float_array_elements) | \
               hynp.arrays(dtype=np.complex128, shape=(length, dim), elements=hy_complex_array_elements)
    if dtype is np.complex128:
        return hynp.arrays(dtype=dtype, shape=(length, dim), elements=hy_complex_array_elements)
    if dtype is np.float64:
        return hynp.arrays(dtype=dtype, shape=(length, dim), elements=hy_float_array_elements)
    raise RuntimeError(f'unsupported dtype={dtype}')


def numpy_vector_spaces(draw, np_data_list, compatible, count, dims):
    return [(NumpyVectorSpace(d), ar) for d, ar in zip(dims, np_data_list)]


def numpy_list_vector_spaces(draw, np_data_list, compatible, count, dims):
    return [(NumpyListVectorSpace(d), ar) for d, ar in zip(dims, np_data_list)]


def block_vector_spaces(draw, np_data_list, compatible, count, dims):
    if not compatible:
        assert count == 2
        block_dims_tuples = draw(hy_block_space_dims_incompat)
    else:
        block_dims_tuples = draw(equal_tuples(hy_block_space_dims, count=count))
    ret = []
    for d, ar in zip(dims, np_data_list):
        # TODO actually compute different blockdims as above
        block_dims = [d]
        constituent_spaces = [NumpyVectorSpace(dim) for dim in block_dims]
        ret.append(BlockVectorSpace(constituent_spaces))
    return ret

_other_vector_space_types = []

if config.HAVE_FENICS:
    def fenics_vector_spaces(draw, np_data_list, compatible, count, dims):
        ret = []
        for d, ar in zip(dims, np_data_list):
            if d < 2:
                continue
            ret.append((FenicsVectorSpace(df.FunctionSpace(df.UnitIntervalMesh(d-1), 'Lagrange', 1)), ar) )
        return ret
    _other_vector_space_types.append('fenics')

if config.HAVE_NGSOLVE:
    def ngsolve_vector_spaces(draw, np_data_list, compatible, count, dims):
        # assert np_data_list[0].dtype == np.float64
        return [(create_ngsolve_space(d), ar) for d, ar in zip(dims, np_data_list)]
    _other_vector_space_types.append('ngsolve')

if config.HAVE_DEALII:
    def dealii_vector_spaces(draw, np_data_list, compatible, count, dims):
        return [(DealIIVectorSpace(d), ar) for d, ar in zip(dims, np_data_list)]
    _other_vector_space_types.append('dealii')

_picklable_vector_space_types = ['numpy', 'numpy_list', 'block']
_picklable_vector_space_types = ['numpy', 'numpy_list']


@hyst.composite
def vector_arrays(draw, count=1, dtype=None, length=None, compatible=True, picklable_only=False):
    dims = draw(hy_dims(count, compatible))
    dtype = dtype or draw(hy_dtypes)
    lngs = draw(length or hyst.tuples(*[hy_lengths for _ in range(count)]))
    np_data_list = [draw(np_arrays(l, dim, dtype=dtype)) for l, dim in zip(lngs, dims)]
    space_types = _picklable_vector_space_types
    if not picklable_only:
        space_types.extend(_other_vector_space_types)
    ret = []
    for space_type in space_types:
        space_data = globals()[f'{space_type}_vector_spaces'](draw, np_data_list, compatible, count, dims)
        vecs = [sp.from_numpy(d) for sp, d in space_data]
        if len(vecs):
            ret.append(vecs)
    return ret



# TODO this needs to be a strategy
def valid_inds(v, length=None):
    if length is None:
        yield []
        yield slice(None)
        yield slice(0, len(v))
        yield slice(0, 0)
        yield slice(-3)
        yield slice(0, len(v), 3)
        yield slice(0, len(v)//2, 2)
        yield list(range(-len(v), len(v)))
        yield list(range(int(len(v)/2)))
        yield list(range(len(v))) * 2
        length = 32
    if len(v) > 0:
        for ind in [-len(v), 0, len(v) - 1]:
            yield ind
        if len(v) == length:
            yield slice(None)
        np.random.seed(len(v) * length)
        yield list(np.random.randint(-len(v), len(v), size=length))
    else:
        if len(v) == 0:
            yield slice(0, 0)
        yield []


# TODO this needs to be a strategy
def valid_inds_of_same_length(v1, v2):
    if len(v1) == len(v2):
        yield slice(None), slice(None)
        yield list(range(len(v1))), list(range(len(v1)))
        yield (slice(0, len(v1)),) * 2
        yield (slice(0, 0),) * 2
        yield (slice(-3),) * 2
        yield (slice(0, len(v1), 3),) * 2
        yield (slice(0, len(v1)//2, 2),) * 2
    yield [], []
    if len(v1) > 0 and len(v2) > 0:
        yield 0, 0
        yield len(v1) - 1, len(v2) - 1
        yield -len(v1), -len(v2)
        yield [0], 0
        yield (list(range(min(len(v1), len(v2))//2)),) * 2
        np.random.seed(len(v1) * len(v2))
        for count in np.linspace(0, min(len(v1), len(v2)), 3).astype(int):
            yield (list(np.random.randint(-len(v1), len(v1), size=count)),
                   list(np.random.randint(-len(v2), len(v2), size=count)))
        yield slice(None), np.random.randint(-len(v2), len(v2), size=len(v1))
        yield np.random.randint(-len(v1), len(v1), size=len(v2)), slice(None)


@hyst.composite
def st_valid_inds_of_same_length(draw, v1, v2):
    len1, len2 = len(v1), len(v2)
    ret = hyst.just([([],), ([],)])
    # TODO we should include integer arrays here by chaining `| hynp.integer_array_indices(shape=(LEN_X,))`
    val1 = hynp.basic_indices(shape=(len1,), allow_ellipsis=False)
    if len1 == len2:
        ret = ret | hyst.tuples(hyst.shared(val1, key="st_valid_inds_of_same_length"), hyst.shared(val1, key="st_valid_inds_of_same_length"))
    if len1 > 0 and len2 > 0:
        val2 = hynp.basic_indices(shape=(len2,), allow_ellipsis=False)
        ret = ret | hyst.tuples(val1, val2)
    # values are always tuples
    return [d[0] for d in draw(ret)]


@hyst.composite
def vector_arrays_with_valid_inds_of_same_length(draw, count=2):
    val = draw(hyst.integers(min_value=1, max_value=MAX_LENGTH))
    length = hyst.tuples(*[hyst.just(val) for _ in range(count)])
    vectors = draw(vector_arrays(count=count, length=length, compatible=True))
    ind = draw(st_valid_inds_of_same_length(*vectors))
    return vectors, ind


# TODO this needs to be a strategy
def valid_inds_of_different_length(v1, v2):
    if len(v1) != len(v2):
        yield slice(None), slice(None)
        yield list(range(len(v1))), list(range(len(v2)))
    if len(v1) > 0 and len(v2) > 0:
        if len(v1) > 1:
            yield [0, 1], 0
            yield [0, 1], [0]
            yield [-1, 0, 1], [0]
            yield slice(0, -1), []
        if len(v2) > 1:
            yield 0, [0, 1]
            yield [0], [0, 1]
        np.random.seed(len(v1) * len(v2))
        for count1 in np.linspace(0, len(v1), 3).astype(int):
            count2 = np.random.randint(0, len(v2))
            if count2 == count1:
                count2 += 1
                if count2 == len(v2):
                    count2 -= 2
            if count2 >= 0:
                yield (list(np.random.randint(-len(v1), len(v1), size=count1)),
                       list(np.random.randint(-len(v2), len(v2), size=count2)))


@hyst.composite
def st_valid_inds_of_different_length(draw, v1, v2):
    len1, len2 = len(v1), len(v2)
    ret = nothing()
    # TODO we should include integer arrays here
    val = hynp.basic_indices(shape=(len1,), allow_ellipsis=False)  # | hynp.integer_array_indices(shape=(len1,))
    if len1 != len2:
        ret = ret | hyst.just((slice(None), slice(None))) \
              | hyst.tuples(hyst.shared(val, key="indfl"), hyst.shared(val, key="indfl"))
    if len1 > 0 and len2 > 0:
        ret = ret | hyst.tuples(val, val).filter(lambda x: len(x[0])!=len(x[1]))
    # values are always tuples
    return [d[0] for d in draw(ret)]


@hyst.composite
def vector_arrays_with_valid_inds_of_different_length(draw, count=2):
    val = draw(hyst.integers(min_value=1, max_value=MAX_LENGTH))
    length = hyst.tuples(*[hyst.just(val) for _ in range(count)])
    vectors = draw(vector_arrays(count=count, length=length, compatible=True))
    ind = draw(st_valid_inds_of_different_length(*vectors))
    return vectors, ind


@hyst.composite
def vector_array_with_ind(draw, ind_length=None, count=1, dtype=None, length=None):
    assert count == 1
    v = draw(vector_arrays(dtype=dtype, length=length), count)
    ind = hyst.sampled_from(list(valid_inds(v[0], ind_length)))
    return (*v, draw(ind))


@hyst.composite
def base_vector_arrays(draw, count=1, dtype=None, max_dim=100):
    """

    Parameters
    ----------
    draw hypothesis control function object
    count how many bases do you want
    dtype dtype for the generated bases, defaults to `np.float_`
    max_dim size limit for the generated

    Returns a list of |VectorArray| linear-independent objects of same dim and length
    -------

    """
    dtype = dtype or np.float_
    # simplest way currently of getting a |VectorSpace| to construct our new arrays from
    space = draw(vector_arrays(count=1, dtype=dtype, length=hyst.just((1,)), compatible=True)
                 .filter(lambda x: x[0].space.dim > 0 and x[0].space.dim < max_dim))[0].space
    length = space.dim
    from scipy.stats import random_correlation
    # this lets hypothesis control np's random state too
    random = draw(hyst.randoms())

    def _eigs():
        """sum must equal to `length` for the scipy construct method"""
        min_eig, max_eig = 0.001, 1.
        eigs = np.asarray((max_eig-min_eig)*np.random.random(length-1) + min_eig, dtype=float)
        return np.append(eigs, [length - np.sum(eigs)])

    if length > 1:
        mat = [random_correlation.rvs(_eigs(), tol=1e-12) for _ in range(count)]
        return [space.from_numpy(m) for m in mat]
    else:
        scalar = 4*np.random.random((1,1))+0.1
        return [space.from_numpy(scalar) for _ in range(count)]


@hyst.composite
def vector_arrays_with_ind_pairs_same_length(draw, count=1, dtype=None, length=None):
    assert count == 1
    v = draw(vector_arrays(dtype=dtype, length=length, count=count))
    ind = list(valid_inds_of_same_length(v[0], v[0]))
    assert len(ind)
    ind = hyst.sampled_from(ind)
    return (*v, draw(ind))


@hyst.composite
def vector_arrays_with_ind_pairs_diff_length(draw, count=1, dtype=None, length=None):
    assert count == 1
    v = draw(vector_arrays(dtype=dtype, length=length), count)
    ind = list(valid_inds_of_different_length(v[0],v[0]))
    if len(ind):
        ind = hyst.sampled_from(ind)
        return (*v, draw(ind))
    return (*v, draw(nothing()))


def vector_arrays_with_ind_pairs_both_lengths(count=1, dtype=None, length=None):
    return vector_arrays_with_ind_pairs_same_length(count, dtype, length) | \
           vector_arrays_with_ind_pairs_diff_length(count, dtype, length)


@hyst.composite
def equal_tuples(draw, strategy, count):
    val = draw(strategy)
    return draw(hyst.tuples(*[hyst.just(val) for _ in range(count)]))


def invalid_inds(v, length=None):
    yield None
    if length is None:
        yield len(v)
        yield [len(v)]
        yield -len(v)-1
        yield [-len(v)-1]
        yield [0, len(v)]
        length = 42
    if length > 0:
        yield [-len(v)-1] + [0, ] * (length - 1)
        yield list(range(length - 1)) + [len(v)]


def invalid_ind_pairs(v1, v2):
    for inds in valid_inds_of_different_length(v1, v2):
        yield inds
    for ind1 in valid_inds(v1):
        for ind2 in invalid_inds(v2, length=v1.len_ind(ind1)):
            yield ind1, ind2
    for ind2 in valid_inds(v2):
        for ind1 in invalid_inds(v1, length=v2.len_ind(ind2)):
            yield ind1, ind2


def st_invalid_ind_pairs(v1, v2):
    return hyst.sampled_from(list(valid_inds_of_different_length(v1, v2))) | \
        hyst.sampled_from([(i1, i2) for i1 in valid_inds(v1) for i2 in invalid_inds(v2, length=v1.len_ind(i1)) ])


@hyst.composite
def vector_arrays_with_invalid_inds(draw, count=2):
    val = draw(hyst.integers(min_value=1, max_value=MAX_LENGTH))
    length = hyst.tuples(*[hyst.just(val) for _ in range(count)])
    vectors = draw(vector_arrays(count=count, length=length, compatible=True))
    ind = draw(st_invalid_ind_pairs(*vectors))
    return vectors, ind
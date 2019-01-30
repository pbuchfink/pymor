# This file is part of the pyMOR project (http://www.pymor.org).
# Copyright 2013-2018 pyMOR developers and contributors. All rights reserved.
# License: BSD 2-Clause License (http://opensource.org/licenses/BSD-2-Clause)

import numpy as np
import pytest

from pymor.operators.numpy import NumpyMatrixOperator


def random_integers(count, seed):
    np.random.seed(seed)
    return list(np.random.randint(0, 3200, count))


def numpy_matrix_operator_with_arrays_factory(dim_source, dim_range, count_source, count_range, seed,
                                              source_id=None, range_id=None):
    np.random.seed(seed)
    op = NumpyMatrixOperator(np.random.random((dim_range, dim_source)), source_id=source_id, range_id=range_id)
    s = op.source.make_array(np.random.random((count_source, dim_source)))
    r = op.range.make_array(np.random.random((count_range, dim_range)))
    return op, None, s, r


def numpy_matrix_operator_with_arrays_and_products_factory(dim_source, dim_range, count_source, count_range, seed,
                                                           source_id=None, range_id=None):
    from scipy.linalg import eigh
    op, _, U, V = numpy_matrix_operator_with_arrays_factory(dim_source, dim_range, count_source, count_range, seed,
                                                            source_id=source_id, range_id=range_id)
    if dim_source > 0:
        while True:
            sp = np.random.random((dim_source, dim_source))
            sp = sp.T.dot(sp)
            evals = eigh(sp, eigvals_only=True)
            if np.min(evals) > 1e-6:
                break
        sp = NumpyMatrixOperator(sp, source_id=source_id, range_id=source_id)
    else:
        sp = NumpyMatrixOperator(np.zeros((0, 0)), source_id=source_id, range_id=source_id)
    if dim_range > 0:
        while True:
            rp = np.random.random((dim_range, dim_range))
            rp = rp.T.dot(rp)
            evals = eigh(rp, eigvals_only=True)
            if np.min(evals) > 1e-6:
                break
        rp = NumpyMatrixOperator(rp, source_id=range_id, range_id=range_id)
    else:
        rp = NumpyMatrixOperator(np.zeros((0, 0)), source_id=range_id, range_id=range_id)
    return op, None, U, V, sp, rp


numpy_matrix_operator_with_arrays_factory_arguments = \
    list(zip([0, 0, 2, 10],           # dim_source
        [0, 1, 4, 10],           # dim_range
        [3, 3, 3, 3],            # count_source
        [3, 3, 3, 3],            # count_range
        random_integers(4, 44)))  # seed


numpy_matrix_operator_with_arrays_generators = \
    [lambda args=args: numpy_matrix_operator_with_arrays_factory(*args)
     for args in numpy_matrix_operator_with_arrays_factory_arguments]


numpy_matrix_operator_generators = \
    [lambda args=args: numpy_matrix_operator_with_arrays_factory(*args)[0:2]
     for args in numpy_matrix_operator_with_arrays_factory_arguments]


def thermalblock_factory(xblocks, yblocks, diameter, seed):
    from pymor.analyticalproblems.thermalblock import thermal_block_problem
    from pymor.discretizers.cg import discretize_stationary_cg
    from pymor.functions.basic import GenericFunction
    from pymor.operators.cg import InterpolationOperator
    p = thermal_block_problem((xblocks, yblocks))
    d, d_data = discretize_stationary_cg(p, diameter)
    f = GenericFunction(lambda X, mu: X[..., 0]**mu['exp'] + X[..., 1],
                        dim_domain=2, parameter_type={'exp': ()})
    iop = InterpolationOperator(d_data['grid'], f)
    U = d.operator.source.empty()
    V = d.operator.range.empty()
    np.random.seed(seed)
    for exp in np.random.random(5):
        U.append(iop.as_vector(exp))
    for exp in np.random.random(6):
        V.append(iop.as_vector(exp))
    return d.operator, d.parameter_space.sample_randomly(1, seed=seed)[0], U, V, d.h1_product, d.l2_product


def thermalblock_assemble_factory(xblocks, yblocks, diameter, seed):
    op, mu, U, V, sp, rp = thermalblock_factory(xblocks, yblocks, diameter, seed)
    return op.assemble(mu), None, U, V, sp, rp


def thermalblock_concatenation_factory(xblocks, yblocks, diameter, seed):
    from pymor.operators.constructions import Concatenation
    op, mu, U, V, sp, rp = thermalblock_factory(xblocks, yblocks, diameter, seed)
    op = sp @ op
    return op, mu, U, V, sp, rp


def thermalblock_identity_factory(xblocks, yblocks, diameter, seed):
    from pymor.operators.constructions import IdentityOperator
    _, _, U, V, sp, rp = thermalblock_factory(xblocks, yblocks, diameter, seed)
    return IdentityOperator(U.space), None, U, V, sp, rp


def thermalblock_zero_factory(xblocks, yblocks, diameter, seed):
    from pymor.operators.constructions import ZeroOperator
    _, _, U, V, sp, rp = thermalblock_factory(xblocks, yblocks, diameter, seed)
    return ZeroOperator(V.space, U.space), None, U, V, sp, rp


def thermalblock_constant_factory(xblocks, yblocks, diameter, seed):
    from pymor.operators.constructions import ConstantOperator
    _, _, U, V, sp, rp = thermalblock_factory(xblocks, yblocks, diameter, seed)
    return ConstantOperator(V[0], U.space), None, U, V, sp, rp


def thermalblock_vectorarray_factory(adjoint, xblocks, yblocks, diameter, seed):
    from pymor.operators.constructions import VectorArrayOperator
    _, _, U, V, sp, rp = thermalblock_factory(xblocks, yblocks, diameter, seed)
    op = VectorArrayOperator(U, adjoint)
    if adjoint:
        U = V
        V = op.range.make_array(np.random.random((7, op.range.dim)))
        sp = rp
        rp = NumpyMatrixOperator(np.eye(op.range.dim) * 2)
    else:
        U = op.source.make_array(np.random.random((7, op.source.dim)))
        sp = NumpyMatrixOperator(np.eye(op.source.dim) * 2)
    return op, None, U, V, sp, rp


def thermalblock_vector_factory(xblocks, yblocks, diameter, seed):
    from pymor.operators.constructions import VectorOperator
    _, _, U, V, sp, rp = thermalblock_factory(xblocks, yblocks, diameter, seed)
    op = VectorOperator(U[0])
    U = op.source.make_array(np.random.random((7, 1)))
    sp = NumpyMatrixOperator(np.eye(1) * 2)
    return op, None, U, V, sp, rp


def thermalblock_vectorfunc_factory(product, xblocks, yblocks, diameter, seed):
    from pymor.operators.constructions import VectorFunctional
    _, _, U, V, sp, rp = thermalblock_factory(xblocks, yblocks, diameter, seed)
    op = VectorFunctional(U[0], product=sp if product else None)
    U = V
    V = op.range.make_array(np.random.random((7, 1)))
    sp = rp
    rp = NumpyMatrixOperator(np.eye(1) * 2)
    return op, None, U, V, sp, rp


def thermalblock_fixedparam_factory(xblocks, yblocks, diameter, seed):
    from pymor.operators.constructions import FixedParameterOperator
    op, mu, U, V, sp, rp = thermalblock_factory(xblocks, yblocks, diameter, seed)
    return FixedParameterOperator(op, mu=mu), None, U, V, sp, rp


thermalblock_factory_arguments = \
    [(2, 2, 1./2., 333),
     (1, 1, 1./4., 444)]


thermalblock_operator_generators = \
    [lambda args=args: thermalblock_factory(*args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_factory(*args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_factory(*args) for args in thermalblock_factory_arguments]


thermalblock_assemble_operator_generators = \
    [lambda args=args: thermalblock_assemble_factory(*args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_assemble_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_assemble_factory(*args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_assemble_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_assemble_factory(*args) for args in thermalblock_factory_arguments]


thermalblock_concatenation_operator_generators = \
    [lambda args=args: thermalblock_concatenation_factory(*args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_concatenation_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_concatenation_factory(*args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_concatenation_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_concatenation_factory(*args) for args in thermalblock_factory_arguments]


thermalblock_identity_operator_generators = \
    [lambda args=args: thermalblock_identity_factory(*args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_zero_operator_generators = \
    [lambda args=args: thermalblock_zero_factory(*args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_constant_operator_generators = \
    [lambda args=args: thermalblock_constant_factory(*args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_identity_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_identity_factory(*args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_zero_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_zero_factory(*args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_constant_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_constant_factory(*args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_identity_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_identity_factory(*args) for args in thermalblock_factory_arguments]


thermalblock_zero_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_zero_factory(*args) for args in thermalblock_factory_arguments]


thermalblock_constant_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_constant_factory(*args) for args in thermalblock_factory_arguments]


thermalblock_vectorarray_operator_generators = \
    [lambda args=args: thermalblock_vectorarray_factory(False, *args)[0:2] for args in thermalblock_factory_arguments] \
    + [lambda args=args: thermalblock_vectorarray_factory(True, *args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_vectorarray_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_vectorarray_factory(False, *args)[0:4] for args in thermalblock_factory_arguments] \
    + [lambda args=args: thermalblock_vectorarray_factory(True, *args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_vectorarray_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_vectorarray_factory(False, *args) for args in thermalblock_factory_arguments] \
    + [lambda args=args: thermalblock_vectorarray_factory(True, *args) for args in thermalblock_factory_arguments]


thermalblock_vector_operator_generators = \
    [lambda args=args: thermalblock_vector_factory(*args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_vector_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_vector_factory(*args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_vector_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_vector_factory(*args) for args in thermalblock_factory_arguments]


thermalblock_vectorfunc_operator_generators = \
    [lambda args=args: thermalblock_vectorfunc_factory(False, *args)[0:2] for args in thermalblock_factory_arguments] \
    + [lambda args=args: thermalblock_vectorfunc_factory(True, *args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_vectorfunc_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_vectorfunc_factory(False, *args)[0:4] for args in thermalblock_factory_arguments] \
    + [lambda args=args: thermalblock_vectorfunc_factory(True, *args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_vectorfunc_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_vectorfunc_factory(False, *args) for args in thermalblock_factory_arguments] \
    + [lambda args=args: thermalblock_vectorfunc_factory(True, *args) for args in thermalblock_factory_arguments]


thermalblock_fixedparam_operator_generators = \
    [lambda args=args: thermalblock_fixedparam_factory(*args)[0:2] for args in thermalblock_factory_arguments]


thermalblock_fixedparam_operator_with_arrays_generators = \
    [lambda args=args: thermalblock_fixedparam_factory(*args)[0:4] for args in thermalblock_factory_arguments]


thermalblock_fixedparam_operator_with_arrays_and_products_generators = \
    [lambda args=args: thermalblock_fixedparam_factory(*args) for args in thermalblock_factory_arguments]


num_misc_operators = 12


def misc_operator_with_arrays_and_products_factory(n):
    if n == 0:
        from pymor.operators.constructions import ComponentProjection
        _, _, U, V, sp, rp = numpy_matrix_operator_with_arrays_and_products_factory(100, 10, 4, 3, n)
        op = ComponentProjection(np.random.randint(0, 100, 10), U.space)
        return op, _, U, V, sp, rp
    elif n == 1:
        from pymor.operators.constructions import ComponentProjection
        _, _, U, V, sp, rp = numpy_matrix_operator_with_arrays_and_products_factory(100, 0, 4, 3, n)
        op = ComponentProjection([], U.space)
        return op, _, U, V, sp, rp
    elif n == 2:
        from pymor.operators.constructions import ComponentProjection
        _, _, U, V, sp, rp = numpy_matrix_operator_with_arrays_and_products_factory(100, 3, 4, 3, n)
        op = ComponentProjection([3, 3, 3], U.space)
        return op, _, U, V, sp, rp
    elif n == 3:
        from pymor.operators.constructions import AdjointOperator
        op, _, U, V, sp, rp = numpy_matrix_operator_with_arrays_and_products_factory(100, 20, 4, 3, n)
        op = AdjointOperator(op, with_apply_inverse=True)
        return op, _, V, U, rp, sp
    elif n == 4:
        from pymor.operators.constructions import AdjointOperator
        op, _, U, V, sp, rp = numpy_matrix_operator_with_arrays_and_products_factory(100, 20, 4, 3, n)
        op = AdjointOperator(op, with_apply_inverse=False)
        return op, _, V, U, rp, sp
    elif 5 <= n <= 7:
        from pymor.operators.constructions import SelectionOperator
        from pymor.parameters.functionals import ProjectionParameterFunctional
        op0, _, U, V, sp, rp = numpy_matrix_operator_with_arrays_and_products_factory(30, 30, 4, 3, n)
        op1 = NumpyMatrixOperator(np.random.random((30, 30)))
        op2 = NumpyMatrixOperator(np.random.random((30, 30)))
        op = SelectionOperator([op0, op1, op2], ProjectionParameterFunctional('x', ()), [0.3, 0.6])
        return op, op.parse_parameter((n-5)/2), V, U, rp, sp
    elif n == 8:
        from pymor.operators.block import BlockDiagonalOperator
        op0, _, U0, V0, sp0, rp0 = numpy_matrix_operator_with_arrays_and_products_factory(10, 10, 4, 3, n)
        op1, _, U1, V1, sp1, rp1 = numpy_matrix_operator_with_arrays_and_products_factory(20, 20, 4, 3, n+1)
        op2, _, U2, V2, sp2, rp2 = numpy_matrix_operator_with_arrays_and_products_factory(30, 30, 4, 3, n+2)
        op = BlockDiagonalOperator([op0, op1, op2])
        sp = BlockDiagonalOperator([sp0, sp1, sp2])
        rp = BlockDiagonalOperator([rp0, rp1, rp2])
        U = op.source.make_array([U0, U1, U2])
        V = op.range.make_array([V0, V1, V2])
        return op, _, U, V, sp, rp
    elif n == 9:
        from pymor.operators.block import BlockDiagonalOperator, BlockOperator
        op0, _, U0, V0, sp0, rp0 = numpy_matrix_operator_with_arrays_and_products_factory(10, 10, 4, 3, n)
        op1, _, U1, V1, sp1, rp1 = numpy_matrix_operator_with_arrays_and_products_factory(20, 20, 4, 3, n+1)
        op2, _, U2, V2, sp2, rp2 = numpy_matrix_operator_with_arrays_and_products_factory(20, 10, 4, 3, n+2)
        op = BlockOperator([[op0, op2],
                            [None, op1]])
        sp = BlockDiagonalOperator([sp0, sp1])
        rp = BlockDiagonalOperator([rp0, rp1])
        U = op.source.make_array([U0, U1])
        V = op.range.make_array([V0, V1])
        return op, None, U, V, sp, rp
    elif n == 10:
        from pymor.operators.block import BlockDiagonalOperator, BlockColumnOperator
        op0, _, U0, V0, sp0, rp0 = numpy_matrix_operator_with_arrays_and_products_factory(10, 10, 4, 3, n)
        op1, _, U1, V1, sp1, rp1 = numpy_matrix_operator_with_arrays_and_products_factory(20, 20, 4, 3, n+1)
        op2, _, U2, V2, sp2, rp2 = numpy_matrix_operator_with_arrays_and_products_factory(20, 10, 4, 3, n+2)
        op = BlockColumnOperator([op2, op1])
        sp = sp1
        rp = BlockDiagonalOperator([rp0, rp1])
        U = U1
        V = op.range.make_array([V0, V1])
        return op, None, U, V, sp, rp
    elif n == 11:
        from pymor.operators.block import BlockDiagonalOperator, BlockRowOperator
        op0, _, U0, V0, sp0, rp0 = numpy_matrix_operator_with_arrays_and_products_factory(10, 10, 4, 3, n)
        op1, _, U1, V1, sp1, rp1 = numpy_matrix_operator_with_arrays_and_products_factory(20, 20, 4, 3, n+1)
        op2, _, U2, V2, sp2, rp2 = numpy_matrix_operator_with_arrays_and_products_factory(20, 10, 4, 3, n+2)
        op = BlockRowOperator([op0, op2])
        sp = BlockDiagonalOperator([sp0, sp1])
        rp = rp0
        U = op.source.make_array([U0, U1])
        V = V0
        return op, None, U, V, sp, rp
    else:
        assert False


num_unpicklable_misc_operators = 1


def unpicklable_misc_operator_with_arrays_and_products_factory(n):
    if n == 0:
        from pymor.operators.numpy import NumpyGenericOperator
        op, _, U, V, sp, rp = numpy_matrix_operator_with_arrays_and_products_factory(100, 20, 4, 3, n)
        mat = op.matrix
        op2 = NumpyGenericOperator(mapping=lambda U: mat.dot(U.T).T, adjoint_mapping=lambda U: mat.T.dot(U.T).T,
                                   dim_source=100, dim_range=20, linear=True)
        return op2, _, U, V, sp, rp
    else:
        assert False


misc_operator_generators = \
    [lambda n=n: misc_operator_with_arrays_and_products_factory(n)[0:2] for n in range(num_misc_operators)]


misc_operator_with_arrays_generators = \
    [lambda n=n: misc_operator_with_arrays_and_products_factory(n)[0:4] for n in range(num_misc_operators)]


misc_operator_with_arrays_and_products_generators = \
    [lambda n=n: misc_operator_with_arrays_and_products_factory(n) for n in range(num_misc_operators)]


unpicklable_misc_operator_generators = \
    [lambda n=n: unpicklable_misc_operator_with_arrays_and_products_factory(n)[0:2]
     for n in range(num_unpicklable_misc_operators)]


unpicklable_misc_operator_with_arrays_generators = \
    [lambda n=n: unpicklable_misc_operator_with_arrays_and_products_factory(n)[0:4]
     for n in range(num_unpicklable_misc_operators)]


unpicklable_misc_operator_with_arrays_and_products_generators = \
    [lambda n=n: unpicklable_misc_operator_with_arrays_and_products_factory(n)
     for n in range(num_unpicklable_misc_operators)]


@pytest.fixture(params=(
    thermalblock_operator_with_arrays_and_products_generators
    + thermalblock_assemble_operator_with_arrays_and_products_generators
    + thermalblock_concatenation_operator_with_arrays_and_products_generators
    + thermalblock_identity_operator_with_arrays_and_products_generators
    + thermalblock_zero_operator_with_arrays_and_products_generators
    + thermalblock_constant_operator_with_arrays_and_products_generators
    + thermalblock_vectorarray_operator_with_arrays_and_products_generators
    + thermalblock_vector_operator_with_arrays_and_products_generators
    + thermalblock_vectorfunc_operator_with_arrays_and_products_generators
    + thermalblock_fixedparam_operator_with_arrays_and_products_generators
    + misc_operator_with_arrays_and_products_generators
    + unpicklable_misc_operator_with_arrays_and_products_generators
))
def operator_with_arrays_and_products(request):
    return request.param()


@pytest.fixture(params=(
    numpy_matrix_operator_with_arrays_generators
    + thermalblock_operator_with_arrays_generators
    + thermalblock_assemble_operator_with_arrays_generators
    + thermalblock_concatenation_operator_with_arrays_generators
    + thermalblock_identity_operator_with_arrays_generators
    + thermalblock_zero_operator_with_arrays_generators
    + thermalblock_constant_operator_with_arrays_generators
    + thermalblock_vectorarray_operator_with_arrays_generators
    + thermalblock_vector_operator_with_arrays_generators
    + thermalblock_vectorfunc_operator_with_arrays_generators
    + thermalblock_fixedparam_operator_with_arrays_generators
    + misc_operator_with_arrays_generators
    + unpicklable_misc_operator_with_arrays_generators
))
def operator_with_arrays(request):
    return request.param()


@pytest.fixture(params=(
    numpy_matrix_operator_generators
    + thermalblock_operator_generators
    + thermalblock_assemble_operator_generators
    + thermalblock_concatenation_operator_generators
    + thermalblock_identity_operator_generators
    + thermalblock_zero_operator_generators
    + thermalblock_constant_operator_generators
    + thermalblock_vectorarray_operator_generators
    + thermalblock_vector_operator_generators
    + thermalblock_vectorfunc_operator_generators
    + thermalblock_fixedparam_operator_generators
    + misc_operator_generators
    + unpicklable_misc_operator_generators
))
def operator(request):
    return request.param()


@pytest.fixture(params=(
    numpy_matrix_operator_generators
    + thermalblock_operator_generators
    + thermalblock_assemble_operator_generators
    + thermalblock_concatenation_operator_generators
    + thermalblock_identity_operator_generators
    + thermalblock_zero_operator_generators
    + thermalblock_constant_operator_generators
    + thermalblock_vectorarray_operator_generators
    + thermalblock_vector_operator_generators
    + thermalblock_vectorfunc_operator_generators
    + thermalblock_fixedparam_operator_generators
    + misc_operator_generators
))
def picklable_operator(request):
    return request.param()

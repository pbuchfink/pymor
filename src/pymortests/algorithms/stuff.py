# This file is part of the pyMOR project (http://www.pymor.org).
# Copyright 2013-2020 pyMOR developers and contributors. All rights reserved.
# License: BSD 2-Clause License (http://opensource.org/licenses/BSD-2-Clause)

import numpy as np
import pytest

from pymor.algorithms.newton import newton, NewtonError
from pymor.tools.floatcmp import float_cmp
from pymor.vectorarrays.numpy import NumpyVectorSpace

from pymortests.base import runmodule
from pymortests.fixtures.operator import MonomOperator


def _newton(order, initial_value=1.0, **kwargs):
    mop = MonomOperator(order)
    rhs = NumpyVectorSpace.from_numpy([0.0])
    guess = NumpyVectorSpace.from_numpy([initial_value])
    return newton(mop, rhs, initial_guess=guess, **kwargs)


@pytest.mark.parametrize("order", list(range(1, 8)))
def test_newton(order):
    U, _ = _newton(order, atol=1e-15)
    assert float_cmp(U.to_numpy(), 0.0)


def test_newton_fail():
    with pytest.raises(NewtonError):
        _ = _newton(0, maxiter=10, stagnation_threshold=np.inf)


def test_newton_residual_is_zero(order=5):
    U, _ = _newton(order, initial_value=0.0)
    assert float_cmp(U.to_numpy(), 0.0)


if __name__ == "__main__":
    runmodule(filename=__file__)

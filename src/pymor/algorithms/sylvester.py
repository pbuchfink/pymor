# -*- coding: utf-8 -*-
# This file is part of the pyMOR project (http://www.pymor.org).
# Copyright 2013-2017 pyMOR developers and contributors. All rights reserved.
# License: BSD 2-Clause License (http://opensource.org/licenses/BSD-2-Clause)

import scipy.linalg as spla

from pymor.algorithms.to_matrix import to_matrix
from pymor.operators.interfaces import OperatorInterface
from pymor.operators.constructions import IdentityOperator, LincombOperator


def solve_sylv_schur(A, Ar, E=None, Er=None, B=None, Br=None, C=None, Cr=None):
    r"""Solve Sylvester equation by Schur decomposition.

    Solves Sylvester equation

    .. math::
        A V E_r^T + E V A_r^T + B B_r^T = 0

    or

    .. math::
        A^T W E_r + E^T W A_r + C^T C_r = 0

    or both using (generalized) Schur decomposition [BKS11]_, if the
    necessary parameters are given.

    .. [BKS11] P. Benner, M. Köhler, J. Saak, Sparse-Dense Sylvester
               Equations in :math:`\mathcal{H}_2`-Model Order
               Reduction,
               Max Planck Institute Magdeburg Preprint, available from
               http://www.mpi-magdeburg.mpg.de/preprints/, 2011.

    Parameters
    ----------
    A
        Real |Operator|.
    Ar
        Real |Operator|.
    E
        Real |Operator| or `None` (then assumed to be the identity).
    Er
        Real |Operator| or `None` (then assumed to be the identity).
    B
        Real |Operator| or `None`.
    Br
        Real |Operator| or `None`.
    C
        Real |Operator| or `None`.
    Cr
        Real |Operator| or `None`.

    Returns
    -------
    V
        Returned if `B` and `Br` are given, |VectorArray| from
        `A.source`.
    W
        Returned if `C` and `Cr` are given, |VectorArray| from
        `A.source`.

    Raises
    ------
    ValueError
        If `V` and `W` cannot be returned.
    """
    # check types
    assert isinstance(A, OperatorInterface) and A.linear and A.source == A.range
    assert isinstance(Ar, OperatorInterface) and Ar.linear and Ar.source == Ar.range

    assert E is None or isinstance(E, OperatorInterface) and E.linear and E.source == E.range == A.source
    if E is None:
        E = IdentityOperator(A.source)
    assert Er is None or isinstance(Er, OperatorInterface) and Er.linear and Er.source == Er.range == Ar.source

    compute_V = B is not None and Br is not None
    compute_W = C is not None and Cr is not None

    if not compute_V and not compute_W:
        raise ValueError('Not enough parameters are given to solve a Sylvester equation.')

    if compute_V:
        assert isinstance(B, OperatorInterface) and B.linear and B.range == A.source
        assert isinstance(Br, OperatorInterface) and Br.linear and Br.range == Ar.source
        assert B.source == Br.source

    if compute_W:
        assert isinstance(C, OperatorInterface) and C.linear and C.source == A.source
        assert isinstance(Cr, OperatorInterface) and Cr.linear and Cr.source == Ar.source
        assert C.range == Cr.range

    # convert reduced operators
    Ar = to_matrix(Ar, format='dense')
    r = Ar.shape[0]
    if Er is not None:
        Er = to_matrix(Er, format='dense')
    if Br is not None:
        Br = Br.as_source_array()
    if Cr is not None:
        Cr = Cr.as_range_array()

    # (Generalized) Schur decomposition
    if Er is None:
        TAr, Z = spla.schur(Ar, output='complex')
        Q = Z
    else:
        TAr, TEr, Q, Z = spla.qz(Ar, Er, output='complex')

    # solve for V, from the last column to the first
    if compute_V:
        V = A.source.empty(reserve=r)

        Br2 = Br.lincomb(Q.T)
        BBr2 = B.apply(Br2)
        for i in range(-1, -r - 1, -1):
            rhs = -BBr2[i].copy()
            if i < -1:
                if Er is not None:
                    rhs -= A.apply(V.lincomb(TEr[i, :i:-1].conjugate()))
                rhs -= E.apply(V.lincomb(TAr[i, :i:-1].conjugate()))
            TErii = 1 if Er is None else TEr[i, i]
            eAaE = LincombOperator([A, E], [TErii.conjugate(), TAr[i, i].conjugate()])
            V.append(eAaE.apply_inverse(rhs))

        V = V.lincomb(Z.conjugate()[:, ::-1])
        V = V.real

    # solve for W, from the first column to the last
    if compute_W:
        W = A.source.empty(reserve=r)

        Cr2 = Cr.lincomb(Z.T)
        CTCr2 = C.apply_adjoint(Cr2)
        for i in range(r):
            rhs = -CTCr2[i].copy()
            if i > 0:
                if Er is not None:
                    rhs -= A.apply_adjoint(W.lincomb(TEr[:i, i]))
                rhs -= E.apply_adjoint(W.lincomb(TAr[:i, i]))
            TErii = 1 if Er is None else TEr[i, i]
            eAaE = LincombOperator([A, E], [TErii.conjugate(), TAr[i, i].conjugate()])
            W.append(eAaE.apply_inverse_adjoint(rhs))

        W = W.lincomb(Q.conjugate())
        W = W.real

    if compute_V and compute_W:
        return V, W
    elif compute_V:
        return V
    else:
        return W

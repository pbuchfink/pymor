# This file is part of the pyMOR project (http://www.pymor.org).
# Copyright 2013-2020 pyMOR developers and contributors. All rights reserved.
# License: BSD 2-Clause License (http://opensource.org/licenses/BSD-2-Clause)

from numbers import Number

import numpy as np

from pymor.core.base import abstractmethod
from pymor.parameters.base import Mu, ParametricObject, Parameters
from pymor.tools.floatcmp import float_cmp


class ParameterFunctional(ParametricObject):
    """Interface for |Parameter| functionals.

    A parameter functional is simply a function mapping |Parameters| to
    a number.
    """

    @abstractmethod
    def evaluate(self, mu=None):
        """Evaluate the functional for given |parameter values| `mu`."""
        pass

    def d_mu(self, parameter, index=0):
        """Return the functionals's derivative with respect to a given parameter.

        Parameters
        ----------
        parameter
            The |Parameter| w.r.t. which to return the derivative.
        index
            Index of the |Parameter|'s component w.r.t which to return the derivative.

        Returns
        -------
        New |ParameterFunctional| representing the partial derivative.
        """
        if parameter not in self.parameters:
            return ConstantParameterFunctional(0, name=self.name + '_d_mu')
        else:
            raise NotImplementedError

    def __call__(self, mu=None):
        return self.evaluate(mu)

    def __mul__(self, other):
        from pymor.parameters.functionals import ProductParameterFunctional
        if not isinstance(other, (Number, ParameterFunctional)):
            return NotImplemented
        return ProductParameterFunctional([self, other])

    __rmul__ = __mul__

    def __neg__(self):
        return self * (-1.)


class ProjectionParameterFunctional(ParameterFunctional):
    """|ParameterFunctional| returning a component value of the given parameter.

    For given parameter map `mu`, this functional evaluates to ::

        mu[parameter][index]


    Parameters
    ----------
    parameter
        The name of the parameter to return.
    size
        The size of the parameter.
    index
        See above.
    name
        Name of the functional.
    """

    def __init__(self, parameter, size=1, index=None, name=None):
        assert isinstance(size, Number)
        if index is None and size == 1:
            index = 0
        assert isinstance(index, Number)
        assert 0 <= index < size

        self.__auto_init(locals())
        self.parameters_own = {parameter: size}

    def evaluate(self, mu=None):
        assert self.parameters.assert_compatible(mu)
        return mu[self.parameter].item(self.index)

    def d_mu(self, parameter, index=0):
        if parameter == self.parameter:
            assert 0 <= index < self.size
            if index == self.index:
                return ConstantParameterFunctional(1, name=self.name + '_d_mu')
        return ConstantParameterFunctional(0, name=self.name + '_d_mu')


class GenericParameterFunctional(ParameterFunctional):
    """A wrapper making an arbitrary Python function a |ParameterFunctional|

    Note that a GenericParameterFunctional can only be :mod:`pickled <pymor.core.pickle>`
    if the function it is wrapping can be pickled. For this reason, it is usually
    preferable to use :class:`ExpressionParameterFunctional` instead of
    :class:`GenericParameterFunctional`.

    Parameters
    ----------
    mapping
        The function to wrap. The function has signature `mapping(mu)`.
    parameters
        The |Parameters| the functional depends on.
    name
        The name of the functional.
    derivative_mappings
        A dict containing all partial derivatives of each |Parameter| and index
        with the signature `derivative_mappings[parameter][index](mu)`
    second_derivative_mappings
        A dict containing all second order partial derivatives of each |Parameter| and index
        with the signature `second_derivative_mappings[parameter_i][index_i][parameter_j][index_j](mu)`
    """

    def __init__(self, mapping, parameters, name=None, derivative_mappings=None, second_derivative_mappings=None):
        self.__auto_init(locals())
        self.parameters_own = parameters

    def evaluate(self, mu=None):
        assert self.parameters.assert_compatible(mu)
        value = self.mapping(mu)
        # ensure that we return a number not an array
        if isinstance(value, np.ndarray):
            return value.item()
        else:
            return value

    def d_mu(self, parameter, index=0):
        if parameter in self.parameters:
            assert 0 <= index < self.parameters[parameter]
            if self.derivative_mappings is None:
                raise ValueError('You must provide a dict of expressions for all \
                                  partial derivatives in self.parameters')
            else:
                if parameter in self.derivative_mappings:
                    if self.second_derivative_mappings is None:
                        return GenericParameterFunctional(
                            self.derivative_mappings[parameter][index],
                            self.parameters, name=self.name + '_d_mu'
                        )
                    else:
                        if parameter in self.second_derivative_mappings:
                            return GenericParameterFunctional(
                                self.derivative_mappings[parameter][index],
                                self.parameters, name=self.name + '_d_mu',
                                derivative_mappings=self.second_derivative_mappings[parameter][index]
                            )
                        else:
                            return GenericParameterFunctional(
                                self.derivative_mappings[parameter][index],
                                self.parameters, name=self.name + '_d_mu',
                                derivative_mappings={}
                            )
                else:
                    raise ValueError('derivative expressions do not contain item {}'.format(parameter))
        return ConstantParameterFunctional(0, name=self.name + '_d_mu')


class ExpressionParameterFunctional(GenericParameterFunctional):
    """Turns a Python expression given as a string into a |ParameterFunctional|.

    Some |NumPy| arithmetic functions like `sin`, `log`, `min` are supported.
    For a full list see the `functions` class attribute.

    .. warning::
       :meth:`eval` is used to evaluate the given expression.
       Using this class with expression strings from untrusted sources will cause
       mayhem and destruction!

    Parameters
    ----------
    expression
        A Python expression in the parameter components of the given `parameters`.
    parameters
        The |Parameters| the functional depends on.
    name
        The name of the functional.
    derivative_expressions
        A dict containing a Python expression for the partial derivatives of each
        parameter component.
    second_derivative_expressions
        A dict containing a list of dicts of Python expressions for all second order partial derivatives of each
        parameter component i and j.
    """

    functions = {k: getattr(np, k) for k in {'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'arctan2',
                                             'sinh', 'cosh', 'tanh', 'arcsinh', 'arccosh', 'arctanh',
                                             'exp', 'exp2', 'log', 'log2', 'log10', 'sqrt', 'array',
                                             'min', 'minimum', 'max', 'maximum', 'pi', 'e',
                                             'sum', 'prod', 'abs', 'sign', 'zeros', 'ones'}}
    functions['norm'] = np.linalg.norm
    functions['polar'] = lambda x: (np.linalg.norm(x, axis=-1), np.arctan2(x[..., 1], x[..., 0]) % (2*np.pi))
    functions['np'] = np

    def __init__(self, expression, parameters, name=None, derivative_expressions=None, second_derivative_expressions=None):
        self.expression = expression
        code = compile(expression, '<expression>', 'eval')
        functions = self.functions

        def get_lambda(exp_code):
            return lambda mu: eval(exp_code, functions, mu)

        exp_mapping = get_lambda(code)
        if derivative_expressions is not None:
            derivative_mappings = derivative_expressions.copy()
            for (key,exp) in derivative_mappings.items():
                exp_array = np.array(exp, dtype=object)
                for exp in np.nditer(exp_array, op_flags=['readwrite'], flags= ['refs_ok']):
                    exp_code = compile(str(exp), '<expression>', 'eval')
                    mapping = get_lambda(exp_code)
                    exp[...] = mapping
                derivative_mappings[key] = exp_array
        else:
            derivative_mappings = None
        if second_derivative_expressions is not None:
            second_derivative_mappings = second_derivative_expressions.copy()
            for (key_i,key_dicts) in second_derivative_mappings.items():
                key_dicts_array = np.array(key_dicts, dtype=object)
                for key_dict in np.nditer(key_dicts_array, op_flags=['readwrite'], flags= ['refs_ok']):
                    for (key_j, exp) in key_dict[()].items():
                        exp_array = np.array(exp, dtype=object)
                        for exp in np.nditer(exp_array, op_flags=['readwrite'], flags= ['refs_ok']):
                            exp_code = compile(str(exp), '<expression>', 'eval')
                            mapping = get_lambda(exp_code)
                            exp[...] = mapping
                        key_dict[()][key_j] = exp_array
                second_derivative_mappings[key_i] = key_dicts_array
        else:
            second_derivative_mappings = None
        super().__init__(exp_mapping, parameters, name, derivative_mappings, second_derivative_mappings)
        self.__auto_init(locals())

    def __reduce__(self):
        return (ExpressionParameterFunctional,
                (self.expression, self.parameters, getattr(self, '_name', None),
                 self.derivative_expressions, self.second_derivative_expressions))


class ProductParameterFunctional(ParameterFunctional):
    """Forms the product of a list of |ParameterFunctionals| or numbers.

    Parameters
    ----------
    factors
        A list of |ParameterFunctionals| or numbers.
    name
        Name of the functional.
    """

    def __init__(self, factors, name=None):
        assert len(factors) > 0
        assert all(isinstance(f, (ParameterFunctional, Number)) for f in factors)
        self.__auto_init(locals())

    def evaluate(self, mu=None):
        assert self.parameters.assert_compatible(mu)
        return np.array([f.evaluate(mu) if hasattr(f, 'evaluate') else f for f in self.factors]).prod()


class ConjugateParameterFunctional(ParameterFunctional):
    """Conjugate of a given |ParameterFunctional|

    Evaluates a given |ParameterFunctional| and returns the complex
    conjugate of the value.

    Parameters
    ----------
    functional
        The |ParameterFunctional| of which the complex conjuate is
        taken.
    name
        Name of the functional.
    """

    def __init__(self, functional, name=None):
        self.functional = functional
        self.name = name or f'{functional.name}_conj'

    def evaluate(self, mu=None):
        assert self.parameters.assert_compatible(mu)
        return np.conj(self.functional.evaluate(mu))


class ConstantParameterFunctional(ParameterFunctional):
    """|ParameterFunctional| returning a constant value for each parameter.

    Parameters
    ----------
    constant_value
        value of the functional
    name
        Name of the functional.
    """

    def __init__(self, constant_value, name=None):
        self.constant_value = constant_value
        self.__auto_init(locals())

    def evaluate(self, mu=None):
        return self.constant_value

    def d_mu(self, parameter, index=0):
        return self.with_(constant_value=0, name=self.name + '_d_mu')


class MinThetaParameterFunctional(ParameterFunctional):
    """|ParameterFunctional| implementing the min-theta approach from [Haa17]_ (Proposition 2.35).

    Let V denote a Hilbert space and let a: V x V -> K denote a parametric coercive bilinear form with affine
    decomposition ::

      a(u, v, mu) = sum_{q = 1}^Q theta_q(mu) a_q(u, v),

    for Q positive coefficient |ParameterFunctional| theta_1, ..., theta_Q and positive semi-definite component
    bilinear forms a_1, ..., a_Q: V x V -> K. Let mu_bar be a parameter with respect to which the coercivity constant
    of a(., ., mu_bar) is known, i.e. we known alpha_mu_bar > 0, s.t. ::

      alpha_mu_bar |u|_V^2 <= a(u, u, mu=mu_bar).

    The min-theta approach from [Haa17]_ (Proposition 2.35) allows to obtain a computable bound for the coercivity
    constant of a(., ., mu) for arbitrary parameters mu, since ::

      a(u, u, mu=mu) >= min_{q = 1}^Q theta_q(mu)/theta_q(mu_bar) a(u, u, mu=mu_bar).

    Given a list of the thetas, the |parameter values| mu_bar and the constant alpha_mu_bar, this functional thus evaluates
    to ::

      alpha_mu_bar * min_{q = 1}^Q theta_q(mu)/theta_q(mu_bar)


    Parameters
    ----------
    thetas
        List or tuple of |ParameterFunctional|
    mu_bar
        Parameter associated with alpha_mu_bar.
    alpha_mu_bar
        Known coercivity constant.
    name
        Name of the functional.
    """

    def __init__(self, thetas, mu_bar, alpha_mu_bar=1., name=None):
        assert isinstance(thetas, (list, tuple))
        assert len(thetas) > 0
        assert all([isinstance(theta, (Number, ParameterFunctional)) for theta in thetas])
        thetas = tuple(ConstantParameterFunctional(theta) if not isinstance(theta, ParameterFunctional) else theta
                       for theta in thetas)
        if not isinstance(mu_bar, Mu):
            mu_bar = Parameters.of(thetas).parse(mu_bar)
        assert Parameters.of(thetas).assert_compatible(mu_bar)
        thetas_mu_bar = np.array([theta(mu_bar) for theta in thetas])
        assert np.all(thetas_mu_bar > 0)
        assert isinstance(alpha_mu_bar, Number)
        assert alpha_mu_bar > 0
        self.__auto_init(locals())
        self.thetas_mu_bar = thetas_mu_bar

    def evaluate(self, mu=None):
        assert self.parameters.assert_compatible(mu)
        thetas_mu = np.array([theta(mu) for theta in self.thetas])
        assert np.all(thetas_mu > 0)
        return self.alpha_mu_bar * np.min(thetas_mu / self.thetas_mu_bar)


class MaxThetaParameterFunctional(ParameterFunctional):
    """|ParameterFunctional| implementing the max-theta approach from [Haa17]_ (Exercise 5.12).

    Let V denote a Hilbert space and let a: V x V -> K denote a continuous bilinear form or l: V -> K a continuous
    linear functional, either with affine decomposition ::

      a(u, v, mu) = sum_{q = 1}^Q theta_q(mu) a_q(u, v)  or  l(v, mu) = sum_{q = 1}^Q theta_q(mu) l_q(v)

    for Q coefficient |ParameterFunctional| theta_1, ..., theta_Q and continuous bilinear forms
    a_1, ..., a_Q: V x V -> K or continuous linear functionals l_q: V -> K. Let mu_bar be a parameter with respect to
    which the continuity constant of a(., ., mu_bar) or l(., mu_bar) is known, i.e. we known gamma_mu_bar > 0, s.t. ::

      a(u, v, mu_bar) <= gamma_mu_bar |u|_V |v|_V  or  l(v, mu_bar) <= gamma_mu_bar |v|_V.

    The max-theta approach from [Haa17]_ (Exercise 5.12) allows to obtain a computable bound for the continuity
    constant of a(., ., mu) or l(., mu) for arbitrary parameters mu, since ::

      a(u, v, mu=mu) <= |max_{q = 1}^Q theta_q(mu)/theta_q(mu_bar)|  |a(u, v, mu=mu_bar)|

    or ::

      l(v, mu=mu) <= |max_{q = 1}^Q theta_q(mu)/theta_q(mu_bar)| |l(v, mu=mu_bar)|,

    if all theta_q(mu_bar) != 0.

    Given a list of the thetas, the |parameter values| mu_bar and the constant gamma_mu_bar, this functional thus evaluates
    to ::

      gamma_mu_bar * max{q = 1}^Q theta_q(mu)/theta_q(mu_bar)


    Parameters
    ----------
    thetas
        List or tuple of |ParameterFunctional|
    mu_bar
        Parameter associated with gamma_mu_bar.
    gamma_mu_bar
        Known continuity constant.
    name
        Name of the functional.
    """

    def __init__(self, thetas, mu_bar, gamma_mu_bar=1., name=None):
        assert isinstance(thetas, (list, tuple))
        assert len(thetas) > 0
        assert all([isinstance(theta, (Number, ParameterFunctional)) for theta in thetas])
        thetas = tuple(ConstantParameterFunctional(f) if not isinstance(f, ParameterFunctional) else f
                       for f in thetas)
        if not isinstance(mu_bar, Mu):
            mu_bar = Parameters.of(thetas).parse(mu_bar)
        assert Parameters.of(thetas).assert_compatible(mu_bar)
        thetas_mu_bar = np.array([theta(mu_bar) for theta in thetas])
        assert not np.any(float_cmp(thetas_mu_bar, 0))
        assert isinstance(gamma_mu_bar, Number)
        assert gamma_mu_bar > 0
        self.__auto_init(locals())
        self.thetas_mu_bar = thetas_mu_bar

    def evaluate(self, mu=None):
        assert self.parameters.assert_compatible(mu)
        thetas_mu = np.array([theta(mu) for theta in self.thetas])
        assert np.all(np.logical_or(thetas_mu < 0, thetas_mu > 0))
        return self.gamma_mu_bar * np.abs(np.max(thetas_mu / self.thetas_mu_bar))

#
# Multi-model Gaussian log pdf
#
# This file is part of PINTS.
#  Copyright (c) 2017-2019, University of Oxford.
#  For licensing information, see the LICENSE file distributed with the PINTS
#  software package.
#
from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals
import pints
import numpy as np
import scipy.stats


class MultimodalGaussianLogPDF(pints.ToyLogPDF):
    """
    Multimodal (un-normalised) multivariate Gaussian distribution.

    By default, the distribution is on a 2-dimensional space, with modes at
    at ``(0, 0)`` and ``(10, 10)`` with independent unit covariance matrices.

    Examples::

        # Default 2d, bimodal
        f = pints.toy.MultimodalGaussianLogPDF()

        # 3d bimodal
        f = pints.toy.MultimodalGaussianLogPDF([[0, 1, 2], [10, 10, 10]])

        # 2d with 3 modes
        f = pints.toy.MultimodalGaussianLogPDF([[0, 0], [5, 5], [5, 0]])

    Arguments:

    ``modes``
        A list of points that will form the modes of the distribution. Must all
        have the same dimension.
        If not set, the method will revert to the bimodal distribution
        described above.
    ``covariances``
        A list of covariance matrices, one for each mode. If not set, a unit
        matrix will be used for each.

    *Extends:* :class:`pints.LogPDF`.
    """
    def __init__(self, modes=None, covariances=None):

        # Check modes
        if modes is None:
            self._n_parameters = 2
            self._modes = [[0, 0], [10, 10]]
        else:
            if len(modes) < 1:
                raise ValueError(
                    'Argument `modes` must be `None` or a non-empty list of'
                    ' modes.')
            self._modes = [pints.vector(mode) for mode in modes]
            self._n_parameters = len(modes[0])
            for mode in self._modes:
                if len(mode) != self._n_parameters:
                    raise ValueError(
                        'All modes must have same dimension.')

        # Check covariances
        if covariances is None:
            self._covs = [np.eye(self._n_parameters)] * len(self._modes)
        else:
            if len(covariances) != len(self._modes):
                raise ValueError(
                    'Number of covariance matrices must equal number of'
                    ' modes.')
            self._covs = [np.array(cov, copy=True) for cov in covariances]
            for cov in self._covs:
                if cov.shape != (self._n_parameters, self._n_parameters):
                    raise ValueError(
                        'Covariance matrices must have shape (d, d), where d'
                        ' is the dimension of the given modes.')

        # Create scipy 'random variables'
        self._vars = [
            scipy.stats.multivariate_normal(mode, self._covs[i])
            for i, mode in enumerate(self._modes)]

        # See page 45 of
        # http://www.math.uwaterloo.ca/~hwolkowi//matrixcookbook.pdf
        self._sigma_invs = [np.linalg.inv(self._covs[i])
                            for i, mode in enumerate(self._modes)]

    def __call__(self, x):
        f = np.sum([var.pdf(x) for var in self._vars])
        return -float('inf') if f == 0 else np.log(f)

    def n_parameters(self):
        """ See :meth:`pints.LogPDF.n_parameters()`. """
        return self._n_parameters

    def sample(self, n_samples):
        """
        See :meth:`ToyLogPDF.sample()`.
        """
        n_samples = int(n_samples)
        if n_samples < 1:
            raise ValueError(
                'Number of samples must be greater than or equal to 1.')

        samples = np.zeros((n_samples, self._n_parameters))
        num_modes = len(self._modes)
        for i in range(n_samples):
            rand_mode = np.random.choice(num_modes, 1)[0]
            samples[i, :] = self._vars[rand_mode].rvs(1)
        return samples

    def evaluateS1(self, x):
        """ See :meth:`LogPDF.evaluateS1()`.
        """
        L = self.__call__(x)

        denom = np.exp(L)
        numer = np.sum([np.matmul(
            self._sigma_invs[i], x - np.array(self._modes[i])
        ) * var.pdf(x)
            for i, var in enumerate(self._vars)], axis=0)
        return L, -numer / denom

    def suggested_bounds(self):
        """
        See :meth:`ToyLogPDF.suggested_bounds()`.
        """
        # make rectangular bounds in each dimension 3X width of range
        a_max = np.max(self._modes)
        a_min = np.min(self._modes)
        a_range = a_max - a_min
        lower = a_min - a_range
        upper = a_max + a_range
        bounds = np.tile([lower, upper], (self._n_parameters, 1))
        return np.transpose(bounds).tolist()

    def kl_divergence(self, samples):
        """
        Calculates the approximate Kullback-Leibler divergence between a
        given list of samples and the distribution underlying this LogPDF. It
        does this by first assigning each point to its most likely mode
        then calculating KL for each mode separately. If one mode is found
        with no near samples then all the samples are used to calculate KL
        for this mode.

        The returned value is (near) zero for perfect sampling, and then
        increases as the error gets larger.

        See: https://en.wikipedia.org/wiki/Kullback-Leibler_divergence
        """
        # Check size of input
        if not len(samples.shape) == 2:
            raise ValueError('Given samples list must be n x 2.')
        if samples.shape[1] != self._n_parameters:
            raise ValueError(
                'Given samples must have length ' + str(self._n_parameters))

        best_mode = np.zeros(samples.shape[0])
        for i in range(samples.shape[0]):
            a_sample = samples[i, :]
            a_log_pdf = -float('Inf')
            a_max_index = -1
            for j, var in enumerate(self._vars):
                a_test_log_pdf = var.logpdf(a_sample)
                if a_test_log_pdf > a_log_pdf:
                    a_log_pdf = a_test_log_pdf
                    a_max_index = j
            best_mode[i] = a_max_index

        kl = np.zeros(len(self._vars))
        for i in range(len(self._vars)):
            y = np.array(samples[best_mode == i, :], copy=True)
            # when a mode has no points use all samples
            if y.shape[0] == 0:
                y = np.array(samples, copy=True)
            m0 = np.mean(y, axis=0)
            s0 = np.cov(y.T)
            s1 = self._covs[i]
            m1 = self._modes[i]
            s1_inv = np.linalg.inv(s1)
            if len(np.atleast_1d(s0)) > 1:
                kl[i] = 0.5 * (
                    np.trace(np.matmul(s1_inv, s0)) +
                    np.matmul(np.matmul(m1 - m0, s1_inv), m1 - m0) -
                    np.log(np.linalg.det(s0)) +
                    np.log(np.linalg.det(s1)) -
                    self._n_parameters)
            else:
                kl[i] = 0.5 * (
                    np.sum(s1_inv * s0) +
                    (m1 - m0) * s1_inv * (m1 - m0) -
                    np.log(s0) +
                    np.log(s1) -
                    1)
        return kl

    def distance(self, samples):
        """
        Calculates per mode approximate KL divergence (see `kl_divergence`)
        then sums these
        """
        kl = self.kl_divergence(samples)
        return np.sum(kl)

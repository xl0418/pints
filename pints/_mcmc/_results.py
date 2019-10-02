#
# MCMC results method
#
# This file is part of PINTS.
#  Copyright (c) 2017-2019, University of Oxford.
#  For licensing information, see the LICENSE file distributed with the PINTS
#  software package.
#
#
from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals
import pints
import numpy as np
from tabulate import tabulate


class MCMCResults(object):
    """
    Wrapper class that calculates key summaries of posterior samples and
    diagnostic quantities from MCMC chains. These include the posterior mean,
    standard deviation, quantiles, rhat, effective sample size and (if
    running time is supplied) effective samples per second.

    References
    ----------
    .. [1] "Inference from iterative simulation using multiple
            sequences", A Gelman and D Rubin, 1992, Statistical Science.
    .. [2] "Bayesian data analysis", 3rd edition, CRC Press.,  A Gelman et al.,
           2014.
    """

    def __init__(self, chains, time=None, parameter_names=None):

        if len(chains) == 1:
            import logging
            logging.basicConfig()
            log = logging.getLogger(__name__)
            log.warning(
                'Summaries calculated with one chain may be unreliable.' +
                ' It is recommended that you rerun sampling with more than' +
                ' one chain')
            shapes = chains[0].shape
            half = int(shapes[0] / 2)
            first = chains[0][0:half, :]
            second = chains[0][half:, :]
            self._chains = [first, second]
        else:
            self._chains = chains
        self._num_params = chains[0].shape[1]

        if time is not None and float(time) <= 0:
            raise ValueError('Elapsed time must be positive.')
        self._time = time

        if parameter_names is not None and (
                self._num_params != len(parameter_names)):
            raise ValueError(
                'Parameter names list must be same length as number of ' +
                'sampled parameters')
        if parameter_names is None:
            parameter_names = (
                ["param " + str(i + 1) for i in range(self._num_params)])
        self._parameter_names = parameter_names

        self._ess = None
        self._ess_per_second = None
        self._mean = None
        self._quantiles = None
        self._rhat = None
        self._std = None
        self._summary_list = []
        self.make_summary()

    def __str__(self):
        """
        Prints posterior summaries for all parameters to the console, including
        the parameter name, posterior mean, posterior std deviation, the
        2.5%, 25%, 50%, 75% and 97.5% posterior quantiles, rhat, effective
        sample size (ess) and ess per second of run time.
        """
        return self._print_summary()

    def chains(self):
        """
        Returns posterior samples from all chains separately.
        """
        return self._chains

    def ess(self):
        """
        Return the effective sample size for each parameter as defined in [2]_.
        """
        return self._ess

    def ess_per_second(self):
        """
        Return the effective sample size (as defined in [2]_) per second of run
        time for each parameter.
        """
        return self._ess_per_second

    def make_summary(self):
        """
        Calculates posterior summaries for all parameters.
        """
        stacked = np.vstack(self._chains)
        self._mean = np.mean(stacked, axis=0)
        self._std = np.std(stacked, axis=0)
        self._quantiles = np.percentile(stacked, [2.5, 25, 50,
                                                  75, 97.5], axis=0)
        self._ess = pints.effective_sample_size(stacked)
        if self._time is not None:
            self._ess_per_second = np.array(self._ess) / self._time
        self._num_chains = len(self._chains)

        self._rhat = pints.rhat_all_params(self._chains)

        if self._time is not None:
            for i in range(0, self._num_params):
                self._summary_list.append([self._parameter_names[i],
                                           self._mean[i],
                                           self._std[i],
                                           self._quantiles[0, i],
                                           self._quantiles[1, i],
                                           self._quantiles[2, i],
                                           self._quantiles[3, i],
                                           self._quantiles[4, i],
                                           self._rhat[i],
                                           self._ess[i],
                                           self._ess_per_second[i]])
        else:
            for i in range(0, self._num_params):
                self._summary_list.append([self._parameter_names[i],
                                           self._mean[i],
                                           self._std[i],
                                           self._quantiles[0, i],
                                           self._quantiles[1, i],
                                           self._quantiles[2, i],
                                           self._quantiles[3, i],
                                           self._quantiles[4, i],
                                           self._rhat[i],
                                           self._ess[i]])

    def mean(self):
        """
        Return the posterior means of all parameters.
        """
        return self._mean

    def _print_summary(self):
        """
        Prints posterior summaries for all parameters to the console, including
        the parameter name, posterior mean, posterior std deviation, the
        2.5%, 25%, 50%, 75% and 97.5% posterior quantiles, rhat, effective
        sample size (ess) and ess per second of run time.
        """
        if self._time is not None:
            return tabulate(self._summary_list,
                            headers=["param", "mean", "std.",
                                     "2.5%", "25%", "50%",
                                     "75%", "97.5%", "rhat",
                                     "ess", "ess per sec."],
                            numalign="left", floatfmt=".2f")
        else:
            return tabulate(self._summary_list,
                            headers=["param", "mean", "std.",
                                     "2.5%", "25%", "50%",
                                     "75%", "97.5%", "rhat",
                                     "ess"],
                            numalign="left", floatfmt=".2f")

    def quantiles(self):
        """
        Return the 2.5%, 25%, 50%, 75% and 97.5% posterior quantiles.
        """
        return self._quantiles

    def rhat(self):
        """
        Return Gelman and Rubin's rhat value as defined in [1]_. If a
        single chain is used, the chain is split into two halves and rhat
        is calculated using these two parts.
        """
        return self._rhat

    def std(self):
        """
        Return the posterior standard deviation of all parameters.
        """
        return self._std

    def summary(self):
        """
        Return a list of the parameter name, posterior mean, posterior std
        deviation, the 2.5%, 25%, 50%, 75% and 97.5% posterior quantiles,
        rhat, effective sample size (ess) and ess per second of run time.
        """
        return self._summary_list

    def time(self):
        """
        Return the run time taken for sampling.
        """
        return self._time

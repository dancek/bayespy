######################################################################
# Copyright (C) 2014 Jaakko Luttinen
#
# This file is licensed under Version 3.0 of the GNU General Public
# License. See LICENSE for a text of the license.
######################################################################

######################################################################
# This file is part of BayesPy.
#
# BayesPy is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# BayesPy is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BayesPy.  If not, see <http://www.gnu.org/licenses/>.
######################################################################

"""
Unit tests for mixture module.
"""

import numpy as np

from ..gaussian import GaussianARD
from ..gamma import Gamma
from ..mixture import Mixture
from ..categorical import Categorical

from bayespy.utils import random
from bayespy.utils import linalg
from bayespy.utils import utils

from bayespy.utils.utils import TestCase

class TestMixture(TestCase):

    def test_init(self):
        """
        Test the creation of Mixture node
        """

        # Do not accept non-negative cluster plates
        z = Categorical(np.ones(2))
        self.assertRaises(ValueError,
                          Mixture,
                          z,
                          GaussianARD, 
                          GaussianARD(0, 1, plates=(2,)),
                          Gamma(1, 1, plates=(2,)),
                          cluster_plate=0)
        
        # Try constructing a mixture without any of the parents having the
        # cluster plate axis
        z = Categorical(np.ones(2))
        self.assertRaises(ValueError,
                          Mixture,
                          z,
                          GaussianARD, 
                          GaussianARD(0, 1, plates=()),
                          Gamma(1, 1, plates=()))
        

    def test_message_to_child(self):
        """
        Test the message to child of Mixture node.
        """

        K = 3

        #
        # Estimate statistics from parents only
        #

        # Simple case
        mu = GaussianARD([0,2,4], 1,
                         ndim=0,
                         plates=(K,))
        alpha = Gamma(1, 1,
                      plates=(K,))
        z = Categorical(np.ones(K))
        X = Mixture(z, GaussianARD, mu, alpha)
        self.assertEqual(X.plates, ())
        self.assertEqual(X.dims, ( (), () ))
        u = X._message_to_child()
        self.assertAllClose(u[0],
                            2)
        self.assertAllClose(u[1],
                            2**2+1)

        # Broadcasting the moments on the cluster axis
        mu = GaussianARD(2, 1,
                         ndim=0,
                         plates=(K,))
        alpha = Gamma(1, 1,
                      plates=(K,))
        z = Categorical(np.ones(K))
        X = Mixture(z, GaussianARD, mu, alpha)
        self.assertEqual(X.plates, ())
        self.assertEqual(X.dims, ( (), () ))
        u = X._message_to_child()
        self.assertAllClose(u[0],
                            2)
        self.assertAllClose(u[1],
                            2**2+1)

        #
        # Estimate statistics with observed children
        #
        
        pass

    def test_message_to_parent(self):
        """
        Test the message to parents of Mixture node.
        """

        K = 3

        # Broadcasting the moments on the cluster axis
        Mu = GaussianARD(2, 1,
                         ndim=0,
                         plates=(K,))
        (mu, mumu) = Mu._message_to_child()
        Alpha = Gamma(3, 1,
                      plates=(K,))
        (alpha, logalpha) = Alpha._message_to_child()
        z = Categorical(np.ones(K))
        X = Mixture(z, GaussianARD, Mu, Alpha)
        tau = 4
        Y = GaussianARD(X, tau)
        y = 5
        Y.observe(y)
        (x, xx) = X._message_to_child()
        m = X._message_to_parent(0)
        self.assertAllClose(m[0],
                            random.gaussian_logpdf(xx*alpha,
                                                   x*alpha*mu,
                                                   mumu*alpha,
                                                   logalpha,
                                                   0))
                                                   
        m = X._message_to_parent(1)
        self.assertAllClose(m[0],
                            1/K * (alpha*x) * np.ones(3))
        self.assertAllClose(m[1],
                            -0.5 * 1/K * alpha * np.ones(3))

        # Some parameters do not have cluster plate axis
        Mu = GaussianARD(2, 1,
                         ndim=0,
                         plates=(K,))
        (mu, mumu) = Mu._message_to_child()
        Alpha = Gamma(3, 1) # Note: no cluster plate axis!
        (alpha, logalpha) = Alpha._message_to_child()
        z = Categorical(np.ones(K))
        X = Mixture(z, GaussianARD, Mu, Alpha)
        tau = 4
        Y = GaussianARD(X, tau)
        y = 5
        Y.observe(y)
        (x, xx) = X._message_to_child()
        m = X._message_to_parent(0)
        self.assertAllClose(m[0],
                            random.gaussian_logpdf(xx*alpha,
                                                   x*alpha*mu,
                                                   mumu*alpha,
                                                   logalpha,
                                                   0))
                                                   
        m = X._message_to_parent(1)
        self.assertAllClose(m[0],
                            1/K * (alpha*x) * np.ones(3))
        self.assertAllClose(m[1],
                            -0.5 * 1/K * alpha * np.ones(3))

        # Cluster assignments do not have as many plate axes as parameters.
        M = 2
        Mu = GaussianARD(2, 1,
                         ndim=0,
                         plates=(K,M))
        (mu, mumu) = Mu._message_to_child()
        Alpha = Gamma(3, 1,
                      plates=(K,M))
        (alpha, logalpha) = Alpha._message_to_child()
        z = Categorical(np.ones(K))
        X = Mixture(z, GaussianARD, Mu, Alpha, cluster_plate=-2)
        tau = 4
        Y = GaussianARD(X, tau)
        y = 5 * np.ones(M)
        Y.observe(y)
        (x, xx) = X._message_to_child()
        m = X._message_to_parent(0)
        self.assertAllClose(m[0]*np.ones(K),
                            np.sum(random.gaussian_logpdf(xx*alpha,
                                                          x*alpha*mu,
                                                          mumu*alpha,
                                                          logalpha,
                                                          0) *
                                   np.ones((K,M)),
                                   axis=-1))
                                                   
        m = X._message_to_parent(1)
        self.assertAllClose(m[0] * np.ones((K,M)),
                            1/K * (alpha*x) * np.ones((K,M)))
        self.assertAllClose(m[1] * np.ones((K,M)),
                            -0.5 * 1/K * alpha * np.ones((K,M)))
        
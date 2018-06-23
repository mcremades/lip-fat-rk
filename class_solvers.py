# Date: 23/06/2018
# Auth: Manuel Cremades, manuel.cremades@usc.es

# Basic modules
import sys; sys.path.insert(0,'..'); from base.basic_import import *

# User defined
from base import class_solvers_nl
from base import class_solvers_sp

import class_butcher
import class_problem

def build(butcher_json, embedded_1, embedded_2):
    '''Instances a solver from a Butcher table.

    Args:
        butcher_json (:obj:`dict`):
        embedded_1 (:obj:`bool`): True if the first method is going to be embedded, False otherwise.
        embedded_2 (:obj:`bool`): True if the second method is going to be embedded, False otherwise.

    Returns:
        solver (:obj:`Solver`):
    '''

    if butcher_json['type'] == 'RW':

        advancing_table = class_butcher.Generalized(butcher_json, embedded_1)
        estimator_table = class_butcher.Generalized(butcher_json, embedded_2)

        solver = RW(advancing_table, estimator_table)

    else:

        advancing_table = class_butcher.Butcher(butcher_json, embedded_1)
        estimator_table = class_butcher.Butcher(butcher_json, embedded_2)

        if butcher_json['type'] == 'DIRK':
            solver = DIRK(advancing_table, estimator_table)
        else:
            if butcher_json['type'] == 'SDIRK':
                solver = SDIRK(advancing_table, estimator_table)
            else:
                if butcher_json['type'] == 'EDIRK':
                    solver = EDIRK(advancing_table, estimator_table)
                else:
                    if butcher_json['type'] == 'ESDIRK':
                        solver = ESDIRK(advancing_table, estimator_table)
                    else:
                        raise NameError('Unknown method or method not implemented yet...')

    return solver

class Solver:
    ''' Abstract class for a solver.

    .. inheritance-diagram:: LM ERK FIRK ESDIRK SDIRK ROW
       :parts: 1
    '''

    def __init__(self):
        pass

class LM(Solver):
    ''' Abstract class for a linear multistep solver.
    '''

    def __init__(self):
        pass

class RK(Solver):
    ''' Abstract class for a Runge-Kutta solver.

    Attributes:
        advancing_table (:obj:`runge_kutta.class_butcher.Butcher`): Butcher table defining the advancing method.
        estimator_table (:obj:`runge_kutta.class_butcher.Butcher`): Butcher table defining the estimator method.
        h_max (:obj:`float`): Maximum step size increasing factor.
        h_min (:obj:`float`): Maximum step size decreasing factor.
        a_tol (:obj:`float`): Absolute tolerance.
        r_tol (:obj:`float`): Relative tolerance.
        s_fac (:obj:`float`): Safety factor used to reduce step rejections.
        q (:obj:`int`): Minimum order of the methods.
        r (:obj:`int`): Maximum order of the methods.
        name (:obj:`str`): Name of the embedded Runge-Kutta method, including type and order of both methods.
    '''

    def __init__(self, advancing_table, estimator_table, a_tol=1e-8, r_tol=1e-3, s_fac=0.8, h_max=5.0, h_min=0.1):

        # Butcher table
        self.advancing_table = advancing_table
        self.estimator_table = estimator_table

        # Absolute and relative tolerances
        self.a_tol = a_tol
        self.r_tol = r_tol

        # Safety factor for time stepping
        self.s_fac = s_fac

        # Bounds for stepsize
        self.h_max = h_max
        self.h_min = h_min

        # Minimum and maximum order of the methods involved
        self.q = min(self.advancing_table.p, self.estimator_table.p)
        self.r = max(self.advancing_table.p, self.estimator_table.p)

        # Name of the method
        self.name = self.__class__.__name__ + str(self.advancing_table.s) + '_' \
                                            + str(self.advancing_table.p) + '(' \
                                            + str(self.estimator_table.p) + ')'

    def solve_fxd(self, problem, state_machine = None, h=None, adj=False, tlm=False):
        '''Solves a problem with fixed step size.

        Args:
            problem (:obj:`runge_kutta.class_problem.Control`)
            h (:obj:`float`): Step size.
            adj (:obj:`bool`): True if adjoint method will be used, False otherwise.
            tlm (:obj:`bool`): True if tangent method will be used, False otherwise.
        '''

        self.adj = adj
        self.tlm = tlm

        if self.adj == True:
            pass
        else:
            self.setup_frw(problem, h)

        if self.tlm == True:
            pass
        else:
            self.setup_tlm(problem, h)

        print "Solving..."

        start = time.time()

        while self.t < self.t_f:

            print 'Time ->', self.t
            print 'Step ->', self.h

            if self.t + self.h > self.t_f:
                self.h = self.t_f - self.t

            self.tstep_frw()

            __, x_0 = self.state_frw(0)
            __, x_k = self.state_frw(self.advancing_table.s - 1)

            if state_machine == None:
                trigged = False
            else:

                params = {'problem': problem, \
                          'x_0': x_0, \
                          'x_k': x_k, \
                          'h_k': self.h, \
                          't_0': self.t}

                x, h, trigged, accept = state_machine.check(params)

            if trigged == True:

                self.h = h[0]

                if accept == True:

                    self.x = x[0]
                    self.t = self.t + self.h

                    if self.tlm == False:
                        self.store_frw(problem)
                    else:
                        self.store_frw(problem)

                        self.tstep_tlm()
                        self.updat_tlm()

                    self.x = problem.solve_initial(self.x)

            else:

                if self.tlm == False:
                    self.updat_frw()
                    self.store_frw(problem)
                else:
                    self.updat_frw()
                    self.store_frw(problem)

                    self.tstep_tlm()
                    self.updat_tlm()

        if self.J == None:
            pass
        else:
            self.cst = self.cst + self.J(self.t, self.x)

        print "Elapsed time: ", time.time() - start

    def solve_adp(self, problem, state_machine = None, h=None, adj=False, tlm=False):
        '''Solves a problem with adaptive step size.

        Args:
            problem (:obj:`runge_kutta.class_problem.Control`)
            h (:obj:`float`): Step size.
            adj (:obj:`bool`): True if adjoint method will be used, False otherwise.
        '''

        raise NameError('Feature not implemented yet...')

    def solve_adj(self, problem, state_machine= None, h=None, adp=False):
        '''Solves an optimization problem and computes the gradient of a cost function by the adjoint method.

        The adjoint state is initialized as

        .. math::
            \\begin{equation}
                \\boldsymbol{\\lambda}_N = \\frac{\\partial J}{\\partial \\mathbf{x}}(\\mathbf{x}_N, \\mathbf{u})
            \\end{equation}

        The gradient of the cost function is initialized as

        .. math::
            \\begin{equation}
                \\nabla{\\Psi} = \\frac{\\partial J}{\\partial \\mathbf{u}}(\\mathbf{x}_N, \\mathbf{u})
            \\end{equation}

        Args:
            problem (:obj:`runge_kutta.class_problem.Control`)
            h (:obj:`float`): Step size.
            adp (:obj:`bool`): True if adaptive step size will be used, False otherwise.
        '''

        raise NameError('Feature not implemented yet...')

    def setup_frw(self, problem, h=None):
        '''Configures the solver for one forward resolution.

        Args:
            problem (:obj:`runge_kutta.class_problem.Problem`)
        '''
        pass

    def setup_adj(self, problem, h=None):
        '''Configures the solver for one adjoint resolution.

        Args:
            problem (:obj:`runge_kutta.class_problem.Control`)
        '''
        pass

    def setup_tlm(self, problem, h=None):
        '''Configures the solver for one tangent resolution.

        Args:
            problem (:obj:`runge_kutta.class_problem.Control`)
        '''
        pass

    def tstep_frw(self):
        '''Performs one forward time step.
        '''
        pass

    def tstep_adj(self):
        '''Performs one adjoint time step.
        '''
        pass

    def tstep_tlm(self):
        '''Performs one tangent time step.
        '''
        pass

    def updat_frw(self):
        '''Update the state and cost function after one forward time step.

        The state is updated as

        .. math::
            \\begin{equation}
        	   \\mathbf{x}_{n+1} = \\mathbf{x}_{n} + \\sum_{i=1}^{s}b_i\\mathbf{k}_i
            \\end{equation}

        once the stage vectors are computed by :meth:`tstep_frw`.

        The cost function is updated as

        .. math::
            \\begin{equation}
        	   \\Psi = \\Psi + h_n \\sum_{i=1}^{s}b_i g(t, \\mathbf{x}_n + \\sum_{j=1}^{s}a_{ij}\\mathbf{k}_j)
            \\end{equation}

        once the stage vectors are computed by :meth:`tstep_frw`.
        '''

        if self.g == None:
             pass

        else:

             for i in range(self.advancing_table.s):

                 t, x = self.state_frw(i)

                 self.cst = self.cst + self.h * self.advancing_table.b[i] * self.g(t, x + self.advancing_table.A[i, i] * self.K[i, :])

        for i in range(self.advancing_table.s):

            self.x = self.x + self.advancing_table.b[i] * self.K[i, :]

        self.t = self.t + self.h

    def updat_bkw(self):
        '''Update the state after one backward time step.

        The state is updated as

        .. math::
            \\begin{equation}
        	   \\mathbf{x}_{n} = \\mathbf{x}_{n + 1} - \\sum_{i=1}^{s}b_i\\mathbf{k}_i
            \\end{equation}

        once the stage vectors are computed by :meth:`tstep_frw`.
        '''

        for i in range(self.advancing_table.s):

            self.x = self.x - self.advancing_table.b[i] * self.K[i, :]

        self.t = self.t - self.h

    def updat_adj(self):
        '''Update the adjoint state and gradient of the cost function after one adjoint time step.
        '''

        self.updat_lmb()
        self.updat_grd()

    def updat_tlm(self):
        '''Update the tangent state after one tangent time step.
        '''
        pass

    def updat_lmb(self):
        '''Update the adjoint state after one adjoint time step.
        '''
        pass

    def updat_grd(self):
        '''Update the gradient of the cost function after one adjoint time step.
        '''
        pass

    def store_frw(self, problem):
        '''Store the state after one forward time step.
        '''

        if self.adj == True:

            self.h_list.append(self.h)
            self.K_list.append(self.K)

        problem.store(self.t, self.x)

    def state_frw(self, i):
        '''Compute :math:`i`-th forward intermediate time and state.
        '''
        x = self.x

        for j in range(i):
            x = x + self.advancing_table.A[i, j] * self.K[j, :]

        t = self.t + self.advancing_table.c[i] * self.h

        return t, x

    def state_bkw(self, i):
        '''Compute :math:`i`-th bckward intermediate time and state.
        '''
        x = self.x

        for j in range(self.advancing_table.s - 1, i, - 1):
            x = x - self.advancing_table.A[i, j] * self.K[j, :]

        t = self.t - self.advancing_table.c[s - i] * self.h

        return t, x

    def adapt(self):
        '''Adjust the step size after one forward time step.
        '''

        self.h = self.h * min(self.h_max, max(self.h_min, self.s_fac * (1.0 / self.error_est) ** (1.0 / (self.q + 1))))

    def check(self, problem):
        '''Check if the local error estimate is under the specified tolerance.
        '''

        x_new = self.x
        y_new = self.x

        for i in range(self.advancing_table.s):

            x_new = x_new + self.advancing_table.b[i] * self.K[i, :]
            y_new = y_new + self.estimator_table.b[i] * self.K[i, :]

        self.error_est = problem.error(x_new, y_new, self.a_tol, self.r_tol)

    def event_frw(self, problem):
        '''
        '''

        for i in range(self.advancing_table.s):

            ti, xi = self.state_frw(i); self.g_1 = problem.check(ti, xi)

            if self.g_0 * self.g_1 < 0.:
                pass
            else:
                self.g_0 = self.g_1

    def event_bkw(self, problem):
        '''
        '''
        pass

    def fd_dfdx(self, t, x):
        '''Computes source derivative with respect to the state by finite differences.
        '''

        raise NameError('Feature not implemented yet...')

    def fd_dMdx(self, t, x, y):
        '''Computes matrix directional derivative with respect to the state by finite differences.

        .. math::
            \\begin{equation}
                \\frac{\partial M}{\partial \\mathbf{x}}(t, \\mathbf{x})\\mathbf{y} = \\lim_{\\epsilon \\rightarrow 0}\\frac{M(t, \\mathbf{x} + \\epsilon\\mathbf{y}) - M(t, \\mathbf{x})}{\\epsilon}
            \\end{equation}
        '''

        raise NameError('Feature not implemented yet...')

class ERK(RK):
    ''' Explicit Runge-Kutta solver.

    .. inheritance-diagram:: LM ERK FIRK ESDIRK SDIRK ROW
       :parts: 1

    The matrix of coefficients defining the method takes the form:

    .. math::
        \\begin{equation}
            \\begin{array}{c|cccc}
            c_1     & 0       & 0       & \\cdots & 0       \\\\
            \\vdots & a_{21}  & 0       & \\ddots & \\vdots \\\\
            \\vdots & \\vdots & \\vdots & \\ddots & 0       \\\\
            c_s     & a_{s1}  & a_{s2}  & \\cdots & 0       \\\\
            \\hline
                    & b_1     & \\cdots & \\cdots & b_s
            \\end{array}
        \\end{equation}
    '''

    def __init__(self, advancing_table, estimator_table):

        class_solvers.RK.__init__(self, advancing_table, estimator_table)

    def updat_lmb(self):
        '''Update the adjoint state after one adjoint time step.
        '''
        pass

    def updat_grd(self):
        '''Update the gradient of the cost function after one adjoint time step.
        '''
        pass

    def tstep_frw(self):
        '''Performs one forward time step.
        '''
        pass

    def tstep_adj(self):
        '''Performs one adjoint time step.
        '''
        pass

    def tstep_tlm(self):
        '''Performs one tangent time step.
        '''
        pass

class IRK(RK):
    ''' Abstract class for a implicit Runge-Kutta solver.

    '''

    def __init__(self, advancing_table, estimator_table):

        RK.__init__(self, advancing_table, estimator_table)

        self.nlsolver = class_solvers_nl.solver_nt()

    def setup_frw(self, problem, h=None):
        '''Configures the solver for one forward resolution.
        '''

        problem.clean()

        self.h = h

        self.t = problem.t_0
        self.x = problem.x_0

        self.M = problem.M
        self.f = problem.f

        if problem.dMdx == None:
            self.dMdx = self.fd_dMdx
        else:
            self.dMdx = problem.dMdx

        if problem.dfdx == None:
            self.dfdx = self.fd_dfdx
        else:
            self.dfdx = problem.dfdx

        self.K = numpy.zeros((self.advancing_table.s, self.x.size))
        self.L = numpy.zeros((self.advancing_table.s, self.x.size))

        if hasattr(problem, 'J'):
            self.J = problem.J
        else:
            self.J = None

        if hasattr(problem, 'g'):
            self.g = problem.g
        else:
            self.g = None

        if hasattr(problem, 'J') or hasattr(problem, 'g'):
            self.cst = 0.

        self.t_0 = problem.t_0
        self.t_f = problem.t_f

        if h == None:
            self.h = (self.t_f - self.t_0) / 100.
        else:
            self.h = h

        self.a_steps = 0
        self.r_steps = 0
        self.d_steps = 0

        self.a_list = []
        self.r_list = []
        self.d_list = []

        self.t_list = []
        self.h_list = []


    def setup_adj(self, problem, h=None):
        '''Configures the solver for one adjoint resolution.
        '''

        self.setup_frw(problem, h)

        self.X = numpy.zeros((self.advancing_table.s, self.x.size))
        self.Y = numpy.zeros((self.advancing_table.s, self.x.size))

        if self.J == None:
            pass
        else:

            if problem.dJdx == None:
                self.dJdx = self.fd_dJdx
            else:
                self.dJdx = problem.dJdx

            if problem.dJdu == None:
                self.dJdu = self.fd_dJdu
            else:
                self.dJdu = problem.dJdu

        if self.g == None:
            pass
        else:

            if problem.dgdx == None:
                self.dgdx = self.fd_dgdx
            else:
                self.dgdx = problem.dgdx

            if problem.dgdu == None:
                self.dgdu = self.fd_dgdu
            else:
                self.dgdu = problem.dgdu

        if problem.dfdu == None:
            self.dfdu = self.fd_dfdu
        else:
            self.dfdu = problem.dfdu

        if problem.dMdu == None:
            raise NameError('Feature not implemented yet...')
        else:
            self.dMdu = problem.dMdu

        self.K_list = []
        self.L_list = []

        self.advancing_table.build_transposed()

class FIRK(IRK):
    ''' Full implicit Runge-Kutta solver.

    The matrix of coefficients defining the method takes the form:

    .. math::
        \\begin{equation}
            \\begin{array}{c|cccc}
            c_1     & a_{11}  & \\cdots & \\cdots & a_{1s}  \\\\
            \\vdots & \\vdots & \\ddots &         & \\vdots \\\\
            \\vdots & \\vdots &         & \\ddots & \\vdots \\\\
            c_s     & a_{s1}  & \\cdots & \\cdots & a_{ss}  \\\\
            \\hline
                    & b_1     & \\cdots & \\cdots & b_s
            \\end{array}
        \\end{equation}
    '''

    def __init__(self, advancing_table, estimator_table):

        IRK.__init__(self, advancing_table, estimator_table)

    def updat_lmb(self):
        '''Update the adjoint state after one adjoint time step.
        '''
        pass

    def updat_grd(self):
        '''Update the gradient of the cost function after one adjoint time step.
        '''
        pass

    def tstep_frw(self):
        '''Performs one forward time step.
        '''
        pass

    def tstep_adj(self):
        '''Performs one adjoint time step.
        '''
        pass

class DIRK(IRK):
    ''' Diagonally implicit Runge-Kutta solver.

    The matrix of coefficients defining the method takes the form:

    .. math::
        \\begin{equation}
            \\begin{array}{c|cccc}
            c_1     & a_{11}  & 0       & \\cdots & 0       \\\\
            \\vdots & a_{21}  & a_{22}  & \\ddots & \\vdots \\\\
            \\vdots & \\vdots & \\vdots & \\ddots & 0       \\\\
            c_s     & a_{s1}  & a_{s2}  & \\cdots & a_{ss}  \\\\
            \\hline
                    & b_1     & \\cdots & \\cdots & b_s
            \\end{array}
        \\end{equation}
    '''

    def __init__(self, advancing_table, estimator_table):

        IRK.__init__(self, advancing_table, estimator_table)

    def updat_lmb(self):
        '''Update the adjoint state after one adjoint time step.

        .. math::
            \\begin{equation}
            \\begin{split}
            \\boldsymbol{\\lambda}_{n} & = \\boldsymbol{\\lambda}_{n+1}                                  \\\\
                                       & + h_n\\sum_{i=1}^{s}b_i\\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{x}}^T(t_{n} + c_ih, \\mathbf{x}_{n} + \sum_{j=1}^{s}a_{ij}\\mathbf{k}_j, \\mathbf{u})\\boldsymbol{\\xi}_{ni} \\\\
                                       & + h_n\\sum_{i=1}^{s}b_i\\frac{\\partial           g}{\\partial \\mathbf{x}}^T(t_{n} + c_ih, \\mathbf{x}_{n} + \sum_{j=1}^{s}a_{ij}\\mathbf{k}_j, \\mathbf{u})
            \\end{split}
            \\end{equation}

        with the matrices pre-computed by :meth:`stage_adj`.
        '''

        for i in range(self.advancing_table.s):

            if self.g == None:

                self.lmb = self.lmb + self.h * self.advancing_table.b[i] * self.dfdx_step[i].transpose().dot(self.X[i, :])

            else:

                self.lmb = self.lmb + self.h * self.advancing_table.b[i] * self.dfdx_step[i].transpose().dot(self.X[i, :]) \
                                    + self.h * self.advancing_table.b[i] * self.dgdx_step[i]

    def updat_grd(self):
        '''Update the gradient of the cost function after one adjoint time step.

        .. math::
            \\begin{equation}
            \\begin{split}
            \\nabla{\\Psi} & = \\nabla{\\Psi}                                 \\\\
                           & + h_n\\sum_{i=1}^{s}b_i\\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{u}}^T(t_{n} + c_ih, \\mathbf{x}_{n} + \sum_{j=1}^{s}a_{ij}\\mathbf{k}_j, \\mathbf{u})\\boldsymbol{\\xi}_{ni} \\\\
                           & + h_n\\sum_{i=1}^{s}b_i\\frac{\\partial           g}{\\partial \\mathbf{u}}^T(t_{n} + c_ih, \\mathbf{x}_{n} + \sum_{j=1}^{s}a_{ij}\\mathbf{k}_j, \\mathbf{u})
            \\end{split}
            \\end{equation}

        with the matrices pre-computed by :meth:`stage_adj`.
        '''

        for i in range(self.advancing_table.s):

            if self.g == None:

                self.grd = self.grd - self.advancing_table.b[i] * (self.dMdu_step[i] - self.h * self.dfdu_step[i]).transpose().dot(self.X[i, :])

            else:

                self.grd = self.grd - self.advancing_table.b[i] * (self.dMdu_step[i] - self.h * self.dfdu_step[i]).transpose().dot(self.X[i, :]) \
                                    + self.h * self.advancing_table.b[i] * self.dgdu_step[i]


    def stage_frw(self, i):
        '''Build one stage function and its derivative with respect to that stage.

        Stage function:

        .. math::
            \\begin{equation}
                \\mathbf{F}_i(\\mathbf{k}_i) = M\\mathbf{k}_i - h\\mathbf{f}(t_n+c_ih,\\mathbf{xx}_n+\sum_{j=1}^{i}a_{ij}\\mathbf{k}_j)
            \\end{equation}

        Stage jacobian:

        .. math::
            \\begin{equation}
                J_i(\\mathbf{k}_i) = M - ha_{ii}\\frac{\\partial \\mathbf{f}}{\\partial\\mathbf{x} }(t_n+c_ih,\\mathbf{x}_n+\sum_{j=1}^{i}a_{ij}\\mathbf{k}_j)
            \\end{equation}

        .. note::
            If :attr:`nlsolver.simplified` = True then only the stage function is returned.

        Args:
            i (:obj:`int`): Index of the intermediate stage.

        Returns:
            (tuple): Tuple containing:

            - **F** (:obj:`function`): Stage function.
            - **J** (:obj:`function`): Stage jacobian.
        '''

        ti, xi = self.state_frw(i)

        def F(x):

            if callable(self.M):
                M = self.M(ti, xi + self.advancing_table.A[i, i] * x)
            else:
                M = self.M

            return M.dot(x) - self.h * self.f(ti, xi + self.advancing_table.A[i, i] * x)

        if self.nlsolver.simplified:

            J = None

        else:

            def J(x):

                if callable(self.M):
                    A = self.advancing_table.A[i, i] * self.dMdx(ti, xi + self.advancing_table.A[i, i] * x, x) + self.M(ti, xi + self.advancing_table.A[i, i] * x)
                else:
                    A = self.M

                if callable(self.dfdx):
                    dfdx = self.dfdx(ti, xi + self.advancing_table.A[i, i] * x)
                else:
                    dfdx = self.dfdx

                return A - self.h * self.advancing_table.A[i, i] * dfdx

        return F, J

    def stage_adj(self):
        '''Compute matrices and vectors required for one adjoint time step.

        In particular, it computes:

        .. math::
            \\begin{equation}
                \\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{x}}(t_n + c_ih, \\mathbf{x}_n + \sum_{j=1}^{i}a_{ij}\\mathbf{k}_j, \\mathbf{u}), \\quad i=1,\\dots, s
            \\end{equation}

        .. math::
            \\begin{equation}
                \\frac{\\partial \\mathbf{g}}{\\partial \\mathbf{u}}(t_n + c_ih, \\mathbf{x}_n + \sum_{j=1}^{i}a_{ij}\\mathbf{k}_j, \\mathbf{u}), \\quad i=1,\\dots, s
            \\end{equation}

        .. math::
            \\begin{equation}
                \\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{x}}(t_n + c_ih, \\mathbf{x}_n + \sum_{j=1}^{i}a_{ij}\\mathbf{k}_j, \\mathbf{u}), \\quad i=1,\\dots, s
            \\end{equation}

        .. math::
            \\begin{equation}
                \\frac{\\partial \\mathbf{g}}{\\partial \\mathbf{u}}(t_n + c_ih, \\mathbf{x}_n + \sum_{j=1}^{i}a_{ij}\\mathbf{k}_j, \\mathbf{u}), \\quad i=1,\\dots, s
            \\end{equation}

        and store all of them in :attr:`dfdx_step`, :attr:`dfdu_step`, :attr:`dgdx_step` and :attr:`dgdu_step` respectively.
        '''

        self.dfdx_step = []
        self.dfdu_step = []

        self.dMdu_step = []

        if self.g == None:
            pass
        else:
            self.dgdx_step = []
            self.dgdu_step = []

        for i in range(self.advancing_table.s):

            t, x = self.state_frw(i)

            self.dfdx_step.append(self.dfdx(t, x + self.advancing_table.A[i, i] * self.K[i, :]))
            self.dfdu_step.append(self.dfdu(t, x + self.advancing_table.A[i, i] * self.K[i, :]))

            self.dMdu_step.append(self.dMdu(t, x + self.advancing_table.A[i, i] * self.K[i, :], self.K[i, :]))

            if self.g == None:
                pass
            else:
                self.dgdx_step.append(self.dgdx(t, x + self.advancing_table.A[i, i] * self.K[i, :]))
                self.dgdu_step.append(self.dgdu(t, x + self.advancing_table.A[i, i] * self.K[i, :]))


    def tstep_frw(self):
        '''Performs one forward time step.

        the forward stages are computed by solving the non-linear systems

        .. math::
            \\begin{equation}
                \\mathbf{F}_i(\\mathbf{k}_i) = M\\mathbf{k}_i - h\\mathbf{f}(t_n+c_ih,\\mathbf{x}_n+\sum_{j=1}^{i}a_{ij}\\mathbf{k}_j),\\quad i=1,\\dots, s
            \\end{equation}

        with jacobians

        .. math::
            \\begin{equation}
                J_i(\\mathbf{k}_i) = M - ha_{ii}\\frac{\\partial \\mathbf{f}}{\\partial\\mathbf{x} }(t_n+c_ih,\\mathbf{x}_n+\sum_{j=1}^{i}a_{ij}\\mathbf{k}_j),\\quad i=1,\\dots, s
            \\end{equation}

        both returned by :meth:`stage_frw` and which are solved sequentially using Newton interations.

        .. note::
            If :attr:`nlsolver.simplified` = True then the matrices

            .. math::
                \\begin{equation}
                    J_i = M - ha_{ii}\\frac{\\partial \\mathbf{f}}{\\partial\\mathbf{x} }(t_n,\\mathbf{x}_n),\\quad i=1,\\dots, s
                \\end{equation}

            are used to perform simplified Newton iterations.
        '''

        if self.nlsolver.simplified:

            if callable(self.M):
                M = self.M(self.t, self.x)
            else:
                M = self.M

            if callable(self.dfdx):
                dfdx = self.dfdx(self.t, self.x)
            else:
                dfdx = self.dfdx

        for i in range(self.advancing_table.s):

            if self.nlsolver.simplified:

                F, _ = self.stage_frw(i); J = M - self.h * self.advancing_table.A[i, i] * dfdx

            else:

                F, J = self.stage_frw(i)

            if i == 0:
                self.K[i, :], ite = self.nlsolver.solve(F, J, self.h * self.f(self.t, self.x))
            else:
                self.K[i, :], ite = self.nlsolver.solve(F, J, self.K[i - 1, :])

            if self.nlsolver.converged:
                pass
            else:
                return

    def tstep_adj(self):
        '''Performs one adjoint time step.

        The adjoint stages are computed by solving the linear systems

        .. math::
            \\begin{equation}
            \\begin{split}
            (M - h_na_{ll}\\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{x}}(t_{nl}, \\mathbf{x}_{nl}, \\mathbf{u}))^T\\boldsymbol{\\xi}_{nl} & = \\boldsymbol{\\lambda}_{n+1}                                  \\\\
                                                           & + h_n\\sum_{i=l+1}^{s}{a}^t_{li}\\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{x}}(t_{ni}, \\mathbf{x}_{ni}, \\mathbf{u})^T\\boldsymbol{\\xi}_{ni} \\\\
                                                           & + h_n\\sum_{i=l+0}^{s}{a}^t_{li}\\frac{\\partial           g}{\\partial \\mathbf{x}}(t_{ni}, \\mathbf{x}_{ni}, \\mathbf{u})^T, \\quad l=1,\\dots, s
            \\end{split}
            \\end{equation}

        with the matrices pre-computed by :meth:`stage_adj`.
        '''

        for i in range(self.advancing_table.s - 1, - 1, - 1):

            if callable(self.M):
                raise NameError('Feature not implemented yet...')
            else:
                A = self.M - self.h * self.advancing_table.A[i, i] * self.dfdx_step[i]

            if self.g == None:

                b = self.lmb

                for j in range(i + 1, self.advancing_table.s):

                    b = b + self.h * self.advancing_table.A_T[i, j] * self.dfdx_step[j].transpose().dot(self.X[j, :])

            else:

                b = self.lmb + self.h * self.advancing_table.A_T[i, i] * self.dgdx_step[i]

                for j in range(i + 1, self.advancing_table.s):

                    b = b + self.h * self.advancing_table.A_T[i, j] * self.dfdx_step[j].transpose().dot(self.X[j, :]) \
                          + self.h * self.advancing_table.A_T[i, j] * self.dgdx_step[j]

            self.X[i, :] = self.nlsolver.solver.solve(A.transpose(), b)

class SDIRK(DIRK):
    ''' Singly diagonally implicit Runge-Kutta solver.

    The matrix of coefficients defining the method takes the form:

    .. math::
        \\begin{equation}
            \\begin{array}{c|cccc}
            c_1     & \\gamma & 0       & \\cdots & 0       \\\\
            \\vdots & a_{21}  & \\gamma & \\ddots & \\vdots \\\\
            \\vdots & \\vdots & \\vdots & \\ddots & 0       \\\\
            c_s     & a_{s1}  & a_{s2}  & \\cdots & \\gamma \\\\
            \\hline
                    & b_1     & \\cdots & \\cdots & b_s
            \\end{array}
        \\end{equation}
    '''

    def __init__(self, advancing_table, estimator_table):

        DIRK.__init__(self, advancing_table, estimator_table)

    def tstep_frw(self):
        '''Performs one forward time step.

        The stages are computed by solving the non-linear systems

        .. math::
            \\begin{equation}
                \\mathbf{F}_i(\\mathbf{k}_i) = M\\mathbf{k}_i - h\\mathbf{f}(t_n+c_ih,\\mathbf{x}_n+\sum_{j=1}^{i}a_{ij}\\mathbf{k}_j),\\quad i=1,\\dots, s
            \\end{equation}

        with jacobians

        .. math::
            \\begin{equation}
                J_i(\\mathbf{k}_i) = M - h\\gamma\\frac{\\partial \\mathbf{f}}{\\partial\\mathbf{x} }(t_n+c_ih,\\mathbf{x}_n+\sum_{j=1}^{i}a_{ij}\\mathbf{k}_j),\\quad i=1,\\dots, s
            \\end{equation}

        both returned by :meth:`stage_frw` and which are solved sequentially using Newton interations.

        .. note::
            If :attr:`nlsolver.simplified` = True then the matrix

            .. math::
                \\begin{equation}
                    J = M - h\\gamma\\frac{\\partial \\mathbf{f}}{\\partial\\mathbf{x} }(t_n,\\mathbf{y}_n)
                \\end{equation}

            is used to perform simplified Newton iterations.
        '''

        if self.nlsolver.simplified:

            if callable(self.M):
                M = self.M(self.t, self.x)
            else:
                M = self.M

            if callable(self.dfdx):
                dfdx = self.dfdx(self.t, self.x)
            else:
                dfdx = self.dfdx

            J = M - self.h * self.advancing_table.A[-1, -1] * dfdx

        for i in range(self.advancing_table.s):

            if self.nlsolver.simplified:

                F, _ = self.stage_frw(i)

            else:

                F, J = self.stage_frw(i)

            if i == 0:
                self.K[i, :], ite = self.nlsolver.solve(F, J, self.h * self.f(self.t, self.x))
            else:
                self.K[i, :], ite = self.nlsolver.solve(F, J, self.K[i - 1, :])

            if self.nlsolver.converged:
                pass
            else:
                return

class EDIRK(DIRK):
    ''' Diagonally implicit Runge-Kutta with an explicit first stage solver.

    The matrix of coefficients defining the method takes the form:

    .. math::
        \\begin{equation}
            \\begin{array}{c|cccc}
            c_1     & 0       & 0       & \\cdots & 0       \\\\
            \\vdots & a_{21}  & a_{22}  & \\ddots & \\vdots \\\\
            \\vdots & \\vdots & \\vdots & \\ddots & 0       \\\\
            c_s     & a_{s1}  & a_{s2}  & \\cdots & a_{ss}  \\\\
            \\hline
                    & b_1     & \\cdots & \\cdots & b_s
            \\end{array}
        \\end{equation}
    '''

    def __init__(self, advancing_table, estimator_table):

        DIRK.__init__(self, advancing_table, estimator_table)

        self.lqsolver = class_solvers_sp.solver_lq()

    def tstep_frw(self):
        '''Performs one forward time step.

        The first stage is computed explicitly as

        .. math::
            \\begin{equation}
                M\\mathbf{k}_1 = h\\mathbf{f}(t_n,\\mathbf{y}_n)
            \\end{equation}

        in contrast with :meth:`SDIRK.tstep_frw`.
        '''

        if callable(self.M):
            M = self.M(self.t, self.x)
        else:
            M = self.M

        self.K[0, :] = self.lqsolver.solve(M, self.h * self.f(self.t, self.x))

        if self.nlsolver.simplified:

            if callable(self.dfdx):
                dfdx = self.dfdx(self.t, self.x)
            else:
                dfdx = self.dfdx

        for i in range(1, self.advancing_table.s):

            if self.nlsolver.simplified:

                F, _ = self.stage_frw(i); J = M - self.h * self.advancing_table.A[i, i] * dfdx

            else:
                F, J = self.stage_frw(i)

            self.K[i, :], ite = self.nlsolver.solve(F, dFdx, self.K[i - 1, :])

            if self.nlsolver.converged:
                pass
            else:
                return

class ESDIRK(DIRK):
    ''' Singly diagonally implicit Runge-Kutta with an explicit first stage solver.

    The matrix of coefficients defining the method takes the form:

    .. math::
        \\begin{equation}
            \\begin{array}{c|cccc}
            c_1     & 0       & 0       & \\cdots & 0       \\\\
            \\vdots & a_{21}  & a_{22}  & \\ddots & \\vdots \\\\
            \\vdots & \\vdots & \\vdots & \\ddots & 0       \\\\
            c_s     & a_{s1}  & a_{s2}  & \\cdots & a_{ss}  \\\\
            \\hline
                    & b_1     & \\cdots & \\cdots & b_s
            \\end{array}
        \\end{equation}
    '''

    def __init__(self, advancing_table, estimator_table):

        DIRK.__init__(self, advancing_table, estimator_table)

        self.lqsolver = class_solvers_sp.solver_lq()

    def tstep_frw(self):
        '''Performs one forward time step.

        The first stage is computed explicitly as

        .. math::
            \\begin{equation}
                M\\mathbf{k}_1 = h\\mathbf{f}(t_n,\\mathbf{y}_n)
            \\end{equation}

        in contrast with :meth:`SDIRK.tstep_frw`.
        '''

        if callable(self.M):
            M = self.M(self.t, self.x)
        else:
            M = self.M

        self.K[0, :] = self.lqsolver.solve(M, self.h * self.f(self.t, self.x))

        if self.nlsolver.simplified:

            if callable(self.dfdx):
                dfdx = self.dfdx(self.t, self.x)
            else:
                dfdx = self.dfdx

            J = M - self.h * self.advancing_table.A[-1, -1] * dfdx

        for i in range(1, self.advancing_table.s):

            if self.nlsolver.simplified:

                F, _ = self.stage_frw(i)

            else:
                F, J = self.stage_frw(i)

            self.K[i, :], ite = self.nlsolver.solve(F, dFdx, self.K[i - 1, :])

            if self.nlsolver.converged:
                pass
            else:
                return

class RW(RK):
    ''' Rosenbrock-Wanner solver.

    The matrix of coefficients defining the method takes the form:

    .. math::
        \\begin{equation}
            \\begin{array}{c|cccc|cccc|c}
            c_1     & a_{11}  & 0       & \\cdots & 0       & \\gamma_{11} & 0            & \\cdots & 0            & d_1     \\\\
            \\vdots & a_{21}  & a_{22}  & \\ddots & \\vdots & \\gamma_{21} & \\gamma_{22} & \\ddots & \\vdots      & \\vdots \\\\
            \\vdots & \\vdots & \\vdots & \\ddots & 0       & \\vdots      & \\vdots      & \\ddots & \\ddots      & \\vdots \\\\
            c_s     & a_{s1}  & a_{s2}  & \\cdots & a_{ss}  & \\gamma_{s1} & \\gamma_{s2} & \\cdots & \\gamma_{ss} & d_s \\\\
            \\hline
                    & b_1     & \\cdots & \\cdots & b_s     &              &              &         &              &
            \\end{array}
        \\end{equation}
    '''

    def __init__(self, advancing_table, estimator_table):

        RK.__init__(self, advancing_table, estimator_table)

        self.spsolver = class_solvers_sp.solver_sp()
        self.lqsolver = class_solvers_sp.solver_lq()

    def setup_frw(self, problem, h=None):
        '''Configures the solver for one forward resolution.
        '''

        problem.clean()

        self.h = h

        self.t = problem.t_0
        self.x = problem.x_0

        self.M = problem.M
        self.f = problem.f

        if problem.dMdx == None:
            self.dMdx = self.fd_dMdx
        else:
            self.dMdx = problem.dMdx

        if problem.dfdx == None:
            self.dfdx = self.fd_dfdx
        else:
            self.dfdx = problem.dfdx

        if problem.dfdt == None:
            self.dfdt = self.fd_dfdt
        else:
            self.dfdt = problem.dfdt

        self.K = numpy.zeros((self.advancing_table.s, self.x.size))
        self.L = numpy.zeros((self.advancing_table.s, self.x.size))

        if hasattr(problem, 'J'):
            self.J = problem.J
        else:
            self.J = None

        if hasattr(problem, 'g'):
            self.g = problem.g
        else:
            self.g = None

        if hasattr(problem, 'J') or hasattr(problem, 'g'):
            self.cst = 0.

        self.t_0 = problem.t_0
        self.t_f = problem.t_f

        if h == None:
            self.h = (self.t_f - self.t_0) / 100.
        else:
            self.h = h

        self.h_list = []
        self.t_list = []

    def setup_adj(self, problem, h=None):
        '''Configures the solver for one adjoint resolution.
        '''

        self.setup_frw(problem, h)

        self.X = numpy.zeros((self.advancing_table.s, self.x.size))
        self.Y = numpy.zeros((self.advancing_table.s, self.x.size))

        if self.J == None:
            pass
        else:

            if problem.dJdx == None:
                self.dJdx = self.fd_dJdx
            else:
                self.dJdx = problem.dJdx

            if problem.dJdu == None:
                self.dJdu = self.fd_dJdu
            else:
                self.dJdu = problem.dJdu

        if self.g == None:
            pass
        else:

            if problem.dgdx == None:
                self.dgdx = self.fd_dgdx
            else:
                self.dgdx = problem.dgdx

            if problem.dgdu == None:
                self.dgdu = self.fd_dgdu
            else:
                self.dgdu = problem.dgdu

        if problem.dfdu == None:
            self.dfdu = self.fd_dfdu
        else:
            self.dfdu = problem.dfdu

        if problem.dMdu == None:
            raise NameError('Feature not implemented yet...')
        else:
            self.dMdu = problem.dMdu

        if problem.d2fdxdx == None:
            self.d2fdxdx = self.fd_d2fdxdx
        else:
            self.d2fdxdx = problem.d2fdxdx

        if problem.d2fdxdt == None:
            self.d2fdxdt = self.fd_d2fdxdt
        else:
            self.d2fdxdt = problem.d2fdxdt

        if problem.d2fdxdu == None:
            self.d2fdxdu = self.fd_d2fdxdu
        else:
            self.d2fdxdu = problem.d2fdxdu

        if problem.d2fdtdu == None:
            self.d2fdtdu = self.fd_d2fdtdu
        else:
            self.d2fdtdu = problem.d2fdtdu

        self.K_list = []
        self.L_list = []

        self.advancing_table.build_transposed()

    def updat_lmb(self):
        '''Update the adjoint state after one adjoint time step.
        '''

        for i in range(self.advancing_table.s):

            if self.g == None:

                self.lmb = self.lmb + self.h * self.advancing_table.b[i] * (self.dfdx_step[i] + self.d2fdxdx_step[i] + self.h * self.advancing_table.d[i] * self.d2fdxdt(self.t, self.x)).transpose().dot(self.X[i, :])

            else:

                self.lmb = self.lmb + self.h * self.advancing_table.b[i] * (self.dfdx_step[i] + self.d2fdxdx_step[i] + self.h * self.advancing_table.d[i] * self.d2fdxdt(self.t, self.x)).transpose().dot(self.X[i, :]) \
                                    + self.h * self.advancing_table.b[i] * self.dgdx_step[i]

    def updat_grd(self):
        '''Update the gradient of the cost function after one adjoint time step.
        '''

        for i in range(self.advancing_table.s):

            if self.g == None:

                self.grd = self.grd - self.advancing_table.b[i] * (self.dMdu_step[i] - self.h * (self.dfdu_step[i] + self.d2fdxdu_step[i] + self.h * self.advancing_table.d[i] * self.d2fdtdu(self.t, self.x))).transpose().dot(self.X[i, :])

            else:

                self.grd = self.grd - self.advancing_table.b[i] * (self.dMdu_step[i] - self.h * (self.dfdu_step[i] + self.d2fdxdu_step[i] + self.h * self.advancing_table.d[i] * self.d2fdtdu(self.t, self.x))).transpose().dot(self.X[i, :]) \
                                    + self.h * self.advancing_table.b[i] * self.dgdu_step[i]

    def stage_adj(self):
        '''Compute matrices and vectors required for one adjoint time step.
        '''

        self.dfdx_step = []
        self.dfdu_step = []

        self.dMdu_step = []

        self.d2fdxdx_step = []
        self.d2fdxdu_step = []

        if self.g == None:
            pass
        else:
            self.dgdx_step = []
            self.dgdu_step = []

        for i in range(self.advancing_table.s):

            t, x = self.state_frw(i)

            self.dfdx_step.append(self.dfdx(t, x + self.advancing_table.A[i, i] * self.K[i, :]))
            self.dfdu_step.append(self.dfdu(t, x + self.advancing_table.A[i, i] * self.K[i, :]))

            self.dMdu_step.append(self.dMdu(t, x + self.advancing_table.A[i, i] * self.K[i, :], self.K[i, :]))

            y = self.x - self.x

            for j in range(i):
                y = y + self.advancing_table.G[i, j] * self.K[j, :]

            self.d2fdxdx_step.append(self.d2fdxdx(self.t, x + self.advancing_table.A[i, i] * self.K[i, :], y + self.advancing_table.G[i, i] * self.K[i, :]))
            self.d2fdxdu_step.append(self.d2fdxdu(self.t, x + self.advancing_table.A[i, i] * self.K[i, :], y + self.advancing_table.G[i, i] * self.K[i, :]))

            if self.g == None:
                pass
            else:
                self.dgdx_step.append(self.dgdx(t, x + self.advancing_table.A[i, i] * self.K[i, :]))
                self.dgdu_step.append(self.dgdu(t, x + self.advancing_table.A[i, i] * self.K[i, :]))

    def tstep_frw(self):
        '''Performs one forward time step.

        The stages are computed by solving the non-linear systems

        .. math::
            \\begin{equation}
                \\begin{split}
                (M-h\\gamma J)\\mathbf{k}_i = & h\\mathbf{f}(t_n + c_ih, \\mathbf{x}_n+\sum_{j=1}^{i-1}a_{ij}\\mathbf{k}_j) + hJ\\sum_{j=1}^{i-1}\\gamma_{ij}\\mathbf{k}_j \\\\
                                          + & h^2d_i\\frac{\\partial \\mathbf{f}}{\\partial t}(t_n, \\mathbf{x}_n),\\quad i=1,\\dots, s
                \\end{split}
            \\end{equation}
        '''

        if callable(self.dfdx):
            dfdx = self.dfdx(self.t, self.x)
        else:
            dfdx = self.dfdx

        if callable(self.M):
            raise NameError('Feature not implemented yet...')
        else:
            M = self.M

        A = M - self.h * self.advancing_table.G[0, 0] * dfdx

        if callable(self.dfdt):
            dfdt = self.dfdt(self.t, self.x)
        else:
            dfdt = self.dfdt

        for i in range(self.advancing_table.s):

            ti, xi = self.state_frw(i)

            y = self.x - self.x

            for j in range(i):
                y = y + self.advancing_table.G[i, j] * self.K[j, :]

            b = self.h * self.f(ti, xi + self.advancing_table.A[i, i] * self.K[i, :]) \
              + self.h * dfdx.dot(y) \
              + self.h ** 2 * self.advancing_table.d[i] * dfdt

            self.K[i, :] = self.spsolver.solve(A, b)

    def tstep_adj(self):
        '''Performs one adjoint time step.
        '''

        if callable(self.M):
            raise NameError('Feature not implemented yet...')
        else:
            A = self.M - self.h * self.advancing_table.G[0, 0] * self.dfdx_step[0]

        for i in range(self.advancing_table.s - 1, - 1, - 1):

            b = self.lmb

            for j in range(i + 1, self.advancing_table.s):

                B_ij = self.advancing_table.A_T[i, j] * self.dfdx_step[j] \
                     + self.advancing_table.G_T[i, j] * self.dfdx_step[0]

                if self.g == None:
                    b = b + self.h * B_ij.transpose().dot(self.X[j, :])
                else:
                    b = b + self.h * B_ij.transpose().dot(self.X[j, :]) + self.h * self.advancing_table.A_T[i, j] * self.dgdx_step[j]

            self.X[i, :] = self.spsolver.solve(A.transpose(), b)

    def fd_dfdt(self, t, x):
        '''Computes source derivative with respect to time by finite differences.

        .. math::
            \\begin{equation}
                \\frac{\partial\\mathbf{f}}{\partial t}(t, \\mathbf{x}) = \\lim_{h\\rightarrow 0}\\frac{\\mathbf{f}(t + h, \\mathbf{x}) - \\mathbf{f}(t, \\mathbf{x})}{h}
            \\end{equation}

        Args:
            t (:obj:`float`): Time.
            x (:obj:`numpy.ndarray`): State.

        Returns:
            dfdt (:obj:`numpy.ndarray`): Source derivatives with respect to time.
        '''

        if self.r < 3:
            # First order
            dfdt = (self.f(t + self.h, x) - self.f(t, x)) / self.h

        elif self.r < 4:
           # Second order
           dfdt = (4.0 * self.f(t + self.h, x) - self.f(t + 2.0 * self.h, x) - 3.0 * self.f(t, x)) / (2.0 * self.h)

        elif self.r < 6:
           # Fourth order
           dfdt = (48.0 * self.f(t + self.h, x) - 36.0 * self.f(t + 2.0 * self.h, x) \
                                                + 16.0 * self.f(t + 3.0 * self.h, x) - 3.0 * self.f(t + 4.0 * self.h, x) - 25.0 * self.f(t, x)) / (12.0 * self.h)

        else:

            print "Possible order reduction, using fourth order finite differences on time..."

            dfdt = (48.0 * self.f(t + self.h, x) - 36.0 * self.f(t + 2.0 * self.h, x) \
                                                 + 16.0 * self.f(t + 3.0 * self.h, x) - 3.0 * self.f(t + 4.0 * self.h, x) - 25.0 * self.f(t, x)) / (12.0 * self.h)

        return dfdt

    def fd_dMdt(self, t, x):
        '''Computes matrix derivative with respect to time by finite differences.

        .. math::
            \\begin{equation}
                \\frac{\partial M}{\partial t}(t, \\mathbf{x}) = \\lim_{h\\rightarrow 0}\\frac{M(t + h, \\mathbf{x}) - M(t, \\mathbf{x})}{h}
            \\end{equation}

        Args:
            t (:obj:`float`): Time.
            x (:obj:`numpy.ndarray`): State.

        Returns:
            dMdt (:obj:`numpy.ndarray`): Matrix derivatives with respect to time.
        '''

        if self.r < 3:
            # First order
            dMdt = (self.M(t + self.h, x) - self.M(t, x)) / self.h

        elif self.r < 4:
            # Second order
            dMdt = (4.0 * self.M(t + self.h, x) - self.M(t + 2.0 * self.h, x) - 3.0 * self.M(t, x)) / (2.0 * self.h)

        elif self.r < 6:
            # Fourth order
            dMdt = (48.0 * self.M(t + self.h, x) - 36.0 * self.M(t + 2.0 * self.h, x) \
                                                 + 16.0 * self.M(t + 3.0 * self.h, x) - 3.0 * self.M(t + 4.0 * self.h, x) - 25.0 * self.M(t, x)) / (12.0 * self.h)

        else:

            print "Possible order reduction, using fourth order finite differences on time..."

            dMdt = (48.0 * self.M(t + self.h, x) - 36.0 * self.M(t + 2.0 * self.h, x) \
                                                 + 16.0 * self.M(t + 3.0 * self.h, x) - 3.0 * self.M(t + 4.0 * self.h, x) - 25.0 * self.M(t, x)) / (12.0 * self.h)

        return dMdt

    def fd_d2fdxdx(self, t, x, y):
        '''Computes source second order directional derivative with respect to state by finite differences.

        .. math::
            \\begin{equation}
                \\frac{\partial^2\\mathbf{f}}{\partial \mathbf{x}^2}(t, \\mathbf{x})\mathbf{y} = \\lim_{\\epsilon\\rightarrow 0}\\frac{\\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{x}}(t, \\mathbf{x} + \\epsilon\\mathbf{y}) - \\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{x}}(t, \\mathbf{x})}{\\epsilon}
            \\end{equation}

        Args:
            t (:obj:`float`): Time.
            x (:obj:`numpy.ndarray`): State.
            y (:obj:`numpy.ndarray`): Direction.

        Returns:
            (:obj:`numpy.ndarray`): Source second order derivatives with respect to state.
        '''

        return (self.dfdx(t, x + self.h * y) - self.dfdx(t, x)) / self.h

    def fd_d2fdxdt(self, t, x):
        '''Computes source second order derivative with respect to time and state by finite differences.

        .. math::
            \\begin{equation}
                \\frac{\partial^2\\mathbf{f}}{\partial \mathbf{x}\partial t}(t, \\mathbf{x}) = \\lim_{h\\rightarrow 0}\\frac{\\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{x}}(t + h, \\mathbf{x}) - \\frac{\\partial \\mathbf{f}}{\\partial \\mathbf{x}}(t, \\mathbf{x})}{h}
            \\end{equation}

        Args:
            t (:obj:`float`): Time.
            x (:obj:`numpy.ndarray`): State.

        Returns:
            (:obj:`numpy.ndarray`): Source second order derivatives with respect to time and state.

        '''

        return (self.dfdx(t + self.h, x) - self.dfdx(t, x)) / self.h

    def fd_d2fdxdu(self, t, x, y):
        '''Computes source second order derivative with respect to the state and control by finite differences.
        '''
        raise NameError('Feature not implemented yet...')

    def fd_d2fdtdu(self, t, x):
        '''Computes source second order derivative with respect to the time and control by finite differences.
        '''
        raise NameError('Feature not implemented yet...')

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('json', help = "Butcher's tables")

    parser.add_argument('-adv', help = "Advancing method, choose 1 or 2.", action = 'store', required = True)
    parser.add_argument('-est', help = "Estimator method, choose 1 or 2.", action = 'store')

    args = parser.parse_args()

    with open(args.json) as data_file:
        butcher_json = json.load(data_file)

    if args.adv == '1':
        embedded_1 = False
        embedded_2 = True
    else:
        if args.adv == '2':
            embedded_1 = True
            embedded_2 = False
        else:
            raise NameError('Choose between 1 or 2 for advancing method...')

    solver = build(butcher_json, embedded_1, embedded_2)

    
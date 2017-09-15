#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 27 13:25:28 2017

@author: levi
"""
import numpy, itsme
from sgra import sgra
from atmosphere import rho
import matplotlib.pyplot as plt

class prob(sgra):

    def initGues(self,opt={}):
        # matrix sizes
        n = 4
        m = 2
        p = 1
        q = 3
        N = 50000+1#20000+1#5000000 + 1 #1000 + 1#

        self.N = N
        self.n = n
        self.m = m
        self.p = p
        self.q = q

        sizes = {'N':N,
                 'n':n,
                 'm':m,
                 'p':p,
                 'q':q}

        dt = 1.0/(N-1)
        t = numpy.arange(0,1.0+dt,dt)
        self.dt = dt
        self.t = t

        # Payload mass
        self.mPayl = 100.0

        # Earth constants
        r_e = 6371.0           # km
        GM = 398600.4415       # km^3 s^-2
        grav_e = GM/r_e/r_e#9.8e-3        # km/s^2

        # rocket constants
        Thrust = 40.0                 # kg km/s²  1.3*m_initial # N

        scal = 1e-2#5.0e-3#7.5e-4# 1.0/2.5e3

        Isp = 450.0                   # s
        s_f = 0.05
        CL0 = 0.0#-0.03                   # (B0 Miele 1998)
        CL1 = 0.8                     # (B1 Miele 1998)
        CD0 = 0.05                    # (A0 Miele 1998)
        CD2 = 0.5                     # (A2 Miele 1998)
        s_ref = numpy.pi*(0.0005)**2  # km^2
        DampCent = 3.0#2.0#
        DampSlop = 3.0


        # boundary conditions
        h_initial = 0.0            # km
        V_initial = 0.0            # km/s
        gamma_initial = numpy.pi/2 # rad
        m_initial = 50000          # kg
        h_final = 463.0   # km
        V_final = numpy.sqrt(GM/(r_e+h_final))#7.633   # km/s
        gamma_final = 0.0 # rad
        #m_final = free   # kg

        boundary = dict()
        boundary['h_initial'] = h_initial
        boundary['V_initial'] = V_initial
        boundary['gamma_initial'] = gamma_initial
        boundary['m_initial'] = m_initial
        boundary['h_final'] = h_final
        boundary['V_final'] = V_final
        boundary['gamma_final'] = gamma_final

        self.boundary = boundary


        constants = dict()
        constants['grav_e'] = grav_e
        constants['Thrust'] = Thrust
        constants['costScalingFactor'] = scal
        constants['Isp'] = Isp
        constants['r_e'] = r_e
        constants['GM'] = GM
        constants['s_f'] = s_f
        constants['CL0'] = CL0
        constants['CL1'] = CL1
        constants['CD0'] = CD0
        constants['CD2'] = CD2
        constants['s_ref'] = s_ref
        constants['DampCent'] = DampCent
        constants['DampSlop'] = DampSlop
        self.constants = constants

        # restrictions
        alpha_min = -2*(numpy.pi)/180  # in rads
        alpha_max = 2*(numpy.pi)/180   # in rads
        beta_min = 0.0
        beta_max = 1.0
        restrictions = dict()
        restrictions['alpha_min'] = alpha_min
        restrictions['alpha_max'] = alpha_max
        restrictions['beta_min'] = beta_min
        restrictions['beta_max'] = beta_max
        self.restrictions = restrictions


        #prepare tolerances
        tolP = 1.0e-7#8
        tolQ = 1.0e-7#5
        tol = dict()
        tol['P'] = tolP
        tol['Q'] = tolQ

        self.tol = tol


        # Get initialization mode
        initMode = opt.get('initMode','default')
        x = numpy.zeros((N,n))
        u = numpy.zeros((N,m))

        if initMode == 'default':
            # artesanal handicraft with L and D (Miele 2003)
            x[:,0] = h_final*numpy.sin(numpy.pi*t/2)
            x[:,1] = 3.793*numpy.exp(0.7256*t) -1.585 -3.661*numpy.cos(3.785*t+0.9552)
            #x[:,1] = V_final*numpy.sin(numpy.pi*t.copy()/2)
            #x[:,1] = 1.0e3*(-0.4523*t.copy()**5 + 1.2353*t.copy()**4-1.1884*t.copy()**3+0.4527*t.copy()**2-0.0397*t.copy())
            x[:,2] = (numpy.pi/2)*(numpy.exp(-(t.copy()**2)/0.017))+0.06419
            x[:,3] = m_initial*((0.7979*numpy.exp(-(t.copy()**2)/0.02))+0.1901*numpy.cos(t.copy()))
            #x[:,3] = m_initial*(1.0-0.89*t.copy())
            #x[:,3] = m_initial*(-2.9*t.copy()**3 + 6.2*t.copy()**2 - 4.2*t.copy() + 1)
            for k in range(N):
                if k<910:
                    u[k,1] = (numpy.pi/2)
                else:
                    if k>4999:
                        u[k,1] = (numpy.pi/2)*0.27
            pi = 1100*numpy.ones((p,1))
            solInit = None

        elif initMode == 'naive':
            pis2 = numpy.pi*0.5
            pi = numpy.array([300.0])
            dt = pi[0]/(N-1); dt6 = dt/6
            x[0,:] = numpy.array([0.0,1.0e-6,pis2,2000.0])
            for i in range(N-1):
                tt = i * dt
                k1 = calcXdot(sizes,tt,x[i,:],u[i,:],constants,restrictions)
                k2 = calcXdot(sizes,tt+.5*dt,x[i,:]+.5*dt*k1,.5*(u[i,:]+u[i+1,:]),constants,restrictions)
                k3 = calcXdot(sizes,tt+.5*dt,x[i,:]+.5*dt*k2,.5*(u[i,:]+u[i+1,:]),constants,restrictions)
                k4 = calcXdot(sizes,tt+dt,x[i,:]+dt*k3,u[i+1,:],constants,restrictions)
                x[i+1,:] = x[i,:] + dt6 * (k1+k2+k2+k3+k3+k4)
            solInit = None
        elif initMode == 'extSol':

            # itsme application
            t_its, x_its, u_its, tabAlpha,\
                tabBeta, inputDict, tphases,\
                mass0, massJet = itsme.sgra('default.its')

            # The inputDict corresponds to the con dictionary from itsme.
            # The con dictionary storages all input information and other
            # informations.
            # massJet: list of jetssoned masses at the beggining of each phase.
            # Solutions must be made compatible: t_its is dimensional,
            # u_its consists of the actual controls (alpha and beta), etc.
            # Besides, all arrays are in a different time discretization

            pi = numpy.array([t_its[-1]])
            t_its = t_its/pi[0]
            u_its = self.calcAdimCtrl(u_its[:,0],u_its[:,1])

            solInit = self.copy()
            solInit.N = len(t_its)
            solInit.t = t_its.copy()
            solInit.x = x_its.copy()
            solInit.u = u_its.copy()
            solInit.pi = pi.copy()

            # Re-integration of proposed solution.
            # Only the controls are used, not the integrated state itself
            dt = pi[0]/(N-1); dt6 = dt/6.0
            x[0,:] = x_its[0,:]
            uip1 = numpy.array([tabAlpha.value(0.0),tabBeta.value(0.0)])
            for i in range(N-1):
                tt = i * dt
                ui = uip1
                u[i,:] = ui
                uipm = numpy.array([tabAlpha.value(tt+.5*dt),tabBeta.value(tt+.5*dt)])
                uip1 = numpy.array([tabAlpha.value(tt+dt),tabBeta.value(tt+dt)])
                if i == N-2:
                    print("Bypassing here...")
                    uip1 = ui
                k1 = calcXdot(sizes,tt,x[i,:],ui,constants,restrictions)
                k2 = calcXdot(sizes,tt+.5*dt,x[i,:]+.5*dt*k1,uipm,constants,restrictions)
                k3 = calcXdot(sizes,tt+.5*dt,x[i,:]+.5*dt*k2,uipm,constants,restrictions)
                k4 = calcXdot(sizes,tt+dt,x[i,:]+dt*k3,uip1,constants,restrictions)
                x[i+1,:] = x[i,:] + dt6 * (k1+k2+k2+k3+k3+k4)

            u[N-1,:] = u[N-2,:]#numpy.array([tabAlpha.value(pi[0]),tabBeta.value(pi[0])])


        lam = 0.0*x.copy()
        mu = numpy.zeros(q)
        u = self.calcAdimCtrl(u[:,0],u[:,1])

        self.x = x
        self.u = u
        self.pi = pi
        self.lam = lam
        self.mu = mu

        self.compWith(solInit,'solZA')

        print("\nInitialization complete.\n")
        return solInit
#%%
    def calcDimCtrl(self):
        # calculate variables alpha (ang. of att.) and beta (prop. thrust)

        restrictions = self.restrictions
        alpha_min = restrictions['alpha_min']
        alpha_max = restrictions['alpha_max']
        beta_min = restrictions['beta_min']
        beta_max = restrictions['beta_max']

        alfa = .5*((alpha_max + alpha_min) + \
                (alpha_max - alpha_min)*numpy.tanh(self.u[:,0]))
        beta = .5*((beta_max + beta_min) +
                (beta_max - beta_min)*numpy.tanh(self.u[:,1]))

        return alfa,beta

    def calcAdimCtrl(self,alfa,beta):
        #u = numpy.empty((self.N,self.m))
        Nu = len(alfa)
        u = numpy.empty((Nu,2))

        restrictions = self.restrictions
        alpha_min = restrictions['alpha_min']
        alpha_max = restrictions['alpha_max']
        beta_min = restrictions['beta_min']
        beta_max = restrictions['beta_max']

        a1 = .5*(alpha_max + alpha_min)
        a2 = .5*(alpha_max - alpha_min)
        b1 = .5*(beta_max + beta_min)
        b2 = .5*(beta_max - beta_min)

        alfa -= a1
        alfa *= 1.0/a2

        beta -= b1
        beta *= 1.0/b2

        u[:,0] = alfa.copy()
        u[:,1] = beta.copy()

        # Basic saturation
        for j in range(2):
            for k in range(Nu):
                if u[k,j] > 0.99999:
                    u[k,j] = 0.99999
                if u[k,j] < -0.99999:
                    u[k,j] = -0.99999

        u = numpy.arctanh(u)
        return u

    def calcPhi(self):
        N = self.N
        n = self.n
        constants = self.constants
        grav_e = constants['grav_e']
        Thrust = constants['Thrust']
        Isp = constants['Isp']
        r_e = constants['r_e']
        GM = constants['GM']
        CL0 = constants['CL0']
        CL1 = constants['CL1']
        CD0 = constants['CD0']
        CD2 = constants['CD2']
        s_ref = constants['s_ref']
        DampCent = constants['DampCent']
        DampSlop = constants['DampSlop']

        sin = numpy.sin
        cos = numpy.cos

        alpha,beta = self.calcDimCtrl()
        x = self.x
        pi = self.pi


        # calculate variables CL and CD
        CL = CL0 + CL1*alpha
        CD = CD0 + CD2*(alpha)**2

        # calculate L and D
        # TODO: making atmosphere.rho vectorized (array compatible) would increase
        # performance significantly!

        dens = numpy.empty(N)
        for k in range(N):
            dens[k] = rho(x[k,0])

        pDynTimesSref = .5 * dens * (x[:,1]**2) * s_ref
        L = CL * pDynTimesSref
        D = CD * pDynTimesSref

        # calculate r
        r = r_e + x[:,0]

        # calculate grav
        grav = GM/r/r

        # calculate phi:
        phi = numpy.empty((N,n))

        # example rocket single stage to orbit with Lift and Drag
        sinGama = sin(x[:,2])
        phi[:,0] = pi[0] * x[:,1] * sinGama
        phi[:,1] = pi[0] * ((beta * Thrust * cos(alpha) - D)/x[:,3] - grav * sinGama)
        phi[:,2] = pi[0] * ((beta * Thrust * sin(alpha) + L)/(x[:,3] * x[:,1]) + cos(x[:,2]) * ( x[:,1]/r  -  grav/x[:,1] ))
    #    phi[0,2] = 0.0
    #    for k in range(N0):
    #        phi[k,2] = 0.0
        dt = 1.0/(N-1)
        t = pi[0]*numpy.arange(0,1.0+dt,dt)
        phi[:,2] = pi[0] * ( (beta * Thrust * sin(alpha) + L)/(x[:,3] * x[:,1]) +
                              cos(x[:,2]) * ( x[:,1]/r  -  grav/x[:,1] )) * \
                   .5*(1.0+numpy.tanh(DampSlop*(t-DampCent)))
        phi[:,3] = - (pi[0] * beta * Thrust)/(grav_e * Isp)

        return phi

#%%

    def calcGrads(self):
        Grads = dict()

        N = self.N
        n = self.n
        m = self.m
        p = self.p
        #q = sizes['q']
        #N0 = sizes['N0']

        # Pre-assign functions
        sin = numpy.sin
        cos = numpy.cos
        tanh = numpy.tanh
        array = numpy.array

        constants = self.constants
        grav_e = constants['grav_e']
        Thrust = constants['Thrust']
        Isp = constants['Isp']
        scal = constants['costScalingFactor']
        r_e = constants['r_e']
        GM = constants['GM']
        s_f = constants['s_f']
        CL0 = constants['CL0']
        CL1 = constants['CL1']
        CD0 = constants['CD0']
        CD2 = constants['CD2']
        s_ref = constants['s_ref']
        DampCent = constants['DampCent']
        DampSlop = constants['DampSlop']

        restrictions = self.restrictions
        alpha_min = restrictions['alpha_min']
        alpha_max = restrictions['alpha_max']
        beta_min = restrictions['beta_min']
        beta_max = restrictions['beta_max']

        u = self.u
        u1 = u[:,0]
        u2 = u[:,1]
        x = self.x
        pi = self.pi


        phix = numpy.zeros((N,n,n))
        phiu = numpy.zeros((N,n,m))

        if p>0:
            phip = numpy.zeros((N,n,p))
        else:
            phip = numpy.zeros((N,n,1))

        fx = numpy.zeros((N,n))
        fu = numpy.zeros((N,m))
        fp = numpy.zeros((N,p))

        psix = array([[1.0,0.0,0.0,0.0],[0.0,1.0,0.0,0.0],[0.0,0.0,1.0,0.0]])
        psip = array([[0.0],[0.0],[0.0]])

        # Calculate variables (arrays) alpha and beta
        aExp = .5*(alpha_max - alpha_min)

        bExp = .5*(beta_max - beta_min)

        alpha,beta = self.calcDimCtrl()

        # calculate variables CL and CD
        CL = CL0 + CL1*alpha
        CD = CD0 + CD2*(alpha)**2

        # calculate L and D; atmosphere: numerical gradient
        dens = numpy.empty(N)
        del_rho = numpy.empty(N)
        for k in range(N):
            dens[k] = rho(x[k,0])
            del_rho[k] = (rho(x[k,0]+.1) - dens[k])/.1

        pDynTimesSref = .5 * dens * (x[:,1]**2) * s_ref
        L = CL * pDynTimesSref
        D = CD * pDynTimesSref

        # calculate r
        r = r_e + x[:,0]

        # calculate grav
        grav = GM/r/r

    #==============================================================================
        for k in range(N):
            sinGama = sin(x[k,2])
            cosGama = cos(x[k,2])

            sinAlpha = sin(alpha[k])
            cosAlpha = cos(alpha[k])

            #cosu1 = cos(u1[k])
            #cosu2 = cos(u2[k])

            r2 = r[k]**2; r3 = r2*r[k]
            V = x[k,1]; V2 = V*V
            m = x[k,3]; m2 = m*m
            fVel = beta[k]*Thrust*cosAlpha-D[k] # forces on velocity direction
            fNor = beta[k]*Thrust*sinAlpha+L[k] # forces normal to velocity
            fdg = .5*(1.0+numpy.tanh(DampSlop*(k*pi[0]/(N-1)-DampCent)))
    #        print("k =",k,", fdg =",fdg)
    #        input("?")
            # Expanded notation:
            DAlfaDu1 = aExp*(1-tanh(u1[k])**2)
            DBetaDu2 = bExp*(1-tanh(u2[k])**2)
    #        if k < N0:# calculated for 3s of no maneuver
    #            phix[k,:,:] = pi[0]*array([[0.0                                                  ,sinGama                   ,V*cosGama         ,0.0      ],
    #                                       [2*GM*sinGama/r3 - (0.5*CD[k]*del_rho[k]*s_ref*V2)/m  ,-CD[k]*dens[k]*s_ref*V/m  ,-grav[k]*cosGama  ,-fVel/m2 ],
    #                                       [0.0                                                  ,0.0                       ,0.0               ,0.0      ],
    #                                       [0.0                                                  ,0.0                       ,0.0               ,0.0      ]])
    #
    #            phiu[k,:,:] = pi[0]*array([[0.0                                  ,0.0                          ],
    #                                       [-beta[k]*Thrust*sinAlpha*DAlfaDu1/m  ,Thrust*cosAlpha*DBetaDu2/m   ],
    #                                       [0.0                                  ,0.0                          ],
    #                                       [0.0                                  ,-Thrust*DBetaDu2/(grav_e*Isp)]])
    #
    #        else:
    #            phix[k,:,:] = pi[0]*array([[0.0                                                              ,sinGama                                                                                        ,V*cosGama                      ,0.0          ],
    #                                       [2*GM*sinGama/r3 - (0.5*CD[k]*del_rho[k]*s_ref*V2)/m              ,-CD[k]*dens[k]*s_ref*V/m                                                                       ,-grav[k]*cosGama               ,-fVel/m2     ],
    #                                       [cosGama*(-V/r2+2*GM/(V*r3)) + (0.5*CL[k]*del_rho[k]*s_ref*V)/m   ,-beta[k]*Thrust*sinAlpha/(m*V2) + cosGama*((1/r[k])+grav[k]/(V2)) + 0.5*CL[k]*dens[k]*s_ref/m  ,-sinGama*((V/r[k])-grav[k]/V)  ,-fNor/(m2*V) ],
    #                                       [0.0                                                              ,0.0                                                                                            ,0.0                            ,0.0          ]])
    #
    #            phiu[k,:,:] = pi[0]*array([[0.0                                                                                ,0.0                           ],
    #                                       [(-beta[k]*Thrust*sinAlpha*DAlfaDu1 - CD2*alpha[k]*dens[k]*s_ref*V2*DAlfaDu1)/m   ,Thrust*cosAlpha*DBetaDu2/m    ],
    #                                       [(beta[k]*Thrust*cosAlpha*DAlfaDu1/V + 0.5*CL1*dens[k]*s_ref*(V)*DAlfaDu1)/m        ,Thrust*sinAlpha*DBetaDu2/(m*V)],
    #                                       [0.0                                                                                ,-Thrust*DBetaDu2/(grav_e*Isp) ]])
            #

            phix[k,:,:] = pi[0]*array([[0.0                                                              ,sinGama                                                                                        ,V*cosGama                      ,0.0          ],
                                       [2*GM*sinGama/r3 - (0.5*CD[k]*del_rho[k]*s_ref*V2)/m              ,-CD[k]*dens[k]*s_ref*V/m                                                                       ,-grav[k]*cosGama               ,-fVel/m2     ],
                                       [cosGama*(-V/r2+2*GM/(V*r3)) + (0.5*CL[k]*del_rho[k]*s_ref*V)/m   ,-beta[k]*Thrust*sinAlpha/(m*V2) + cosGama*((1/r[k])+grav[k]/(V2)) + 0.5*CL[k]*dens[k]*s_ref/m  ,-sinGama*((V/r[k])-grav[k]/V)  ,-fNor/(m2*V) ],
                                       [0.0                                                              ,0.0                                                                                            ,0.0                            ,0.0          ]])
            phix[k,2,:] *= fdg
            phiu[k,:,:] = pi[0]*array([[0.0                                                        ,0.0                           ],
                 [(-beta[k]*Thrust*sinAlpha*DAlfaDu1 - CD2*alpha[k]*dens[k]*s_ref*V2*DAlfaDu1)/m   ,Thrust*cosAlpha*DBetaDu2/m    ],
                 [(beta[k]*Thrust*cosAlpha*DAlfaDu1/V + 0.5*CL1*dens[k]*s_ref*(V)*DAlfaDu1)/m      ,Thrust*sinAlpha*DBetaDu2/(m*V)],
                 [0.0                                                                              ,-Thrust*DBetaDu2/(grav_e*Isp) ]])
            phiu[k,2,:] *= fdg
            phip[k,:,:] = array([[V*sinGama                                   ],
                                 [fVel/m - grav[k]*sinGama                    ],
                                 [fNor/(m*V) + cosGama*((V/r[k])-(grav[k]/V)) ],
                                 [-(beta[k]*Thrust)/(grav_e*Isp)              ]])
            phip[k,2,:] *= fdg
            fu[k,:] = array([0.0,(pi[0]*Thrust*DBetaDu2)/(grav_e * Isp * (1-s_f))])
            fp[k,0] = (Thrust * beta[k])/(grav_e * Isp * (1-s_f))
    #==============================================================================

        Grads['phix'] = phix
        Grads['phiu'] = phiu
        Grads['phip'] = phip
        Grads['fx'] = fx*scal
        Grads['fu'] = fu*scal
        Grads['fp'] = fp*scal
    #    Grads['gx'] = gx
    #    Grads['gp'] = gp
        Grads['psix'] = psix
        Grads['psip'] = psip
        return Grads

#%%
    def calcPsi(self):
        boundary = self.boundary
        x = self.x
        N = self.N
        psi = numpy.array([x[N-1,0]-boundary['h_final'],\
                           x[N-1,1]-boundary['V_final'],\
                           x[N-1,2]-boundary['gamma_final']])
        return psi

    def calcF(self):
        constants = self.constants
        grav_e = constants['grav_e']
        Thrust = constants['Thrust']
        Isp = constants['Isp']
        s_f = constants['s_f']
        scal = constants['costScalingFactor']
        restrictions = self.restrictions
        beta_min = restrictions['beta_min']
        beta_max = restrictions['beta_max']
        #u1 = u[:,0]
        u2 = self.u[:,1]

        # calculate variable beta
        beta = (beta_max + beta_min)/2 + numpy.tanh(u2)*(beta_max - beta_min)/2

        # example rocket single stage to orbit with Lift and Drag
        f = scal*((Thrust * self.pi[0])/(grav_e * (1.0-s_f) * Isp)) * beta

        return f

    def calcI(self):
        N = self.N
        f = self.calcF()
        I = f.sum()
        I -= .5*(f[0]+f[N-1])
        I *= 1.0/(N-1)

        return I
#%%
    def plotSol(self,opt={},intv=[]):
        t = self.t
        x = self.x
        u = self.u
        pi = self.pi

        if len(intv)==0:
            intv = numpy.arange(0,self.N,1,dtype='int')
        else:
             intv = list(intv)

        plt.subplot2grid((8,4),(0,0),colspan=5)
        plt.plot(t[intv],x[intv,0])
        plt.grid(True)
        plt.ylabel("h [km]")
        if opt.get('mode','sol') == 'sol':
            I = self.calcI()
            titlStr = "Current solution: I = {:.4E}".format(I) + \
            " P = {:.4E} ".format(self.P) + " Q = {:.4E} ".format(self.Q)
#            titlStr = "Current solution: I = {:.4E}".format(I)
#            if opt.get('dispP',False):
#                P = opt['P']
#                titlStr = titlStr + " P = {:.4E} ".format(P)
#            if opt.get('dispQ',False):
#                Q = opt['Q']
#                titlStr = titlStr + " Q = {:.4E} ".format(Q)
        elif opt['mode'] == 'var':
            titlStr = "Proposed variations"
        else:
            titlStr = opt['mode']
        #
        plt.title(titlStr)

        plt.subplot2grid((8,4),(1,0),colspan=5)
        plt.plot(t[intv],x[intv,1],'g')
        plt.grid(True)
        plt.ylabel("V [km/s]")

        plt.subplot2grid((8,4),(2,0),colspan=5)
        plt.plot(t[intv],x[intv,2]*180/numpy.pi,'r')
        plt.grid(True)
        plt.ylabel("gamma [deg]")

        plt.subplot2grid((8,4),(3,0),colspan=5)
        plt.plot(t[intv],x[intv,3],'m')
        plt.grid(True)
        plt.ylabel("m [kg]")

        plt.subplot2grid((8,4),(4,0),colspan=5)
        plt.plot(t[intv],u[intv,0],'k')
        plt.grid(True)
        plt.ylabel("u1 [-]")

        plt.subplot2grid((8,4),(5,0),colspan=5)
        plt.plot(t[intv],u[intv,1],'c')
        plt.grid(True)
        plt.xlabel("t")
        plt.ylabel("u2 [-]")

        ######################################
        alpha,beta = self.calcDimCtrl()
        alpha *= 180.0/numpy.pi
        plt.subplot2grid((8,4),(6,0),colspan=5)
        plt.plot(t[intv],alpha[intv],'b')
        #plt.hold(True)
        #plt.plot(t,alpha*0+alpha_max*180/numpy.pi,'-.k')
        #plt.plot(t,alpha*0+alpha_min*180/numpy.pi,'-.k')
        plt.grid(True)
        plt.xlabel("t")
        plt.ylabel("alpha [deg]")

        plt.subplot2grid((8,4),(7,0),colspan=5)
        plt.plot(t[intv],beta[intv],'b')
        #plt.hold(True)
        #plt.plot(t,beta*0+beta_max,'-.k')
        #plt.plot(t,beta*0+beta_min,'-.k')
        plt.grid(True)
        plt.xlabel("t")
        plt.ylabel("beta [-]")
        ######################################
        plt.subplots_adjust(0.0125,0.0,0.9,2.5,0.2,0.2)
        plt.show()
        print("pi =",pi)
        print("Final rocket mass: {:.4E}\n".format(x[-1,3]))
    #

    def compWith(self,altSol,altSolLabl='altSol'):
        print("\nComparing solutions...\n")
        currSolLabl = 'currentSol'

        plt.plot(altSol.t,altSol.x[:,0],label=altSolLabl)
        plt.plot(self.t,self.x[:,0],'--y',label=currSolLabl)
        plt.grid()
        plt.ylabel("h [km]")
        plt.xlabel("t [-]")
        plt.title('Height')
        plt.legend()
        plt.show()

        plt.plot(altSol.t,altSol.x[:,1],label=altSolLabl)
        plt.plot(self.t,self.x[:,1],'--g',label=currSolLabl)
        plt.grid()
        plt.ylabel("V [km/s]")
        plt.xlabel("t [-]")
        plt.title('Absolute speed')
        plt.legend()
        plt.show()

        plt.plot(altSol.t,altSol.x[:,2]*180/numpy.pi,label=altSolLabl)
        plt.plot(self.t,self.x[:,2]*180/numpy.pi,'--r',label=currSolLabl)
        plt.grid()
        plt.ylabel("gamma [deg]")
        plt.xlabel("t [-]")
        plt.title('Flight path angle')
        plt.legend()
        plt.show()

        plt.plot(altSol.t,altSol.x[:,3],label=altSolLabl)
        plt.plot(self.t,self.x[:,3],'--m',label=currSolLabl)
        plt.grid()
        plt.ylabel("m [kg]")
        plt.xlabel("t [-]")
        plt.title('Rocket mass')
        plt.legend()
        plt.show()

        alpha,beta = self.calcDimCtrl()
        alpha_alt,beta_alt = altSol.calcDimCtrl()
        plt.plot(altSol.t,alpha_alt*180/numpy.pi,label=altSolLabl)
        plt.plot(self.t,alpha*180/numpy.pi,'--g',label=currSolLabl)
        plt.grid()
        plt.xlabel("t [-]")
        plt.ylabel("alfa [deg]")
        plt.title('Attack angle')
        plt.legend()
        plt.show()

        plt.plot(altSol.t,beta_alt,label=altSolLabl)
        plt.plot(self.t,beta,'--k',label=currSolLabl)
        plt.grid()
        plt.xlabel("t [-]")
        plt.ylabel("beta [-]")
        plt.title('Thrust profile')
        plt.legend()
        plt.show()

        print("Final rocket mass:")
        mFinSol, mFinAlt = self.x[self.N-1,3], altSol.x[altSol.N-1,3]
        print(currSolLabl+": {:.4E}".format(mFinSol)+" kg.")
        print(altSolLabl+": {:.4E}".format(mFinAlt)+" kg.")
        print("Difference: {:.4E}".format(mFinSol-mFinAlt)+" kg, "+\
              "{:.4G}".format(100.0*(mFinSol-mFinAlt)/self.mPayl)+\
              "% more payload!\n")


    def plotTraj(self):

        cos = numpy.cos
        sin = numpy.sin
        R = self.constants['r_e']
        N = self.N
        dt = self.dt * self.pi # Dimensional dt...

        X = numpy.empty(N)
        Z = numpy.empty(N)

        sigma = 0.0 #sigma: range angle
        X[0] = 0.0
        Z[0] = 0.0

        # Propulsive phases' starting and ending times
        isBurn = True
        indBurn = [0]
        indShut = []
        for i in range(1,N):
            if isBurn:
                if self.u[i,1] < -.999:
                    isBurn = False
                    indShut.append(i)
            else: #not burning
                if self.u[i,1] > -.999:
                    isBurn = True
                    indBurn.append(i)

            # Propagate the trajectory by Euler method.
            v = self.x[i,1]
            gama = self.x[i,2]
            dsigma = v * cos(gama) / (R+self.x[i,0])
            sigma += dsigma*dt

            X[i] = X[i-1] + dt * v * cos(gama-sigma)
            Z[i] = Z[i-1] + dt * v * sin(gama-sigma)
        #
        indShut.append(N-1)

        # Draw Earth segment corresponding to flight range
        s = numpy.arange(0,1.01,.01) * sigma
        x = R * cos(.5*numpy.pi - s)
        z = R * (sin(.5*numpy.pi - s) - 1.0)
        plt.plot(x,z,'k')

        # Get final orbit parameters
        h,v,gama,M = self.x[N-1,:]

        print("State @burnout time:")
        print("h = {:.4E}".format(h)+", v = {:.4E}".format(v)+\
        ", gama = {:.4E}".format(gama)+", m = {:.4E}".format(M))

        GM = self.constants['GM']
        r = R + h
#        print("Final altitude:",h)
        cosGama = cos(gama)
        sinGama = sin(gama)
        momAng = r * v * cosGama
#        print("Ang mom:",momAng)
        en = .5 * v * v - GM/r
#        print("Energy:",en)
        a = - .5*GM/en
#        print("Semi-major axis:",a)
        aux = v * momAng / GM
        e = numpy.sqrt((aux * cosGama - 1.0)**2 + (aux * sinGama)**2)
        print("Eccentricity:",e)
        eccExpr = v * momAng * cosGama/GM - 1.0
#        print("r =",r)
        f = numpy.arccos(eccExpr/e)
        print("True anomaly:",f*180/numpy.pi)
        ph = a * (1.0 - e) - R
        print("Perigee altitude:",ph)
        ah = 2*(a - R) - ph
        print("Apogee altitude:",ah)

        # semi-latus rectum
        p = momAng**2 / GM #a * (1.0-e)**2


        # Plot orbit in green over the same range as the Earth shown
        # (and a little but futher)

        s = numpy.arange(f-1.2*sigma,f+.2*sigma,.01)
#        print("s =",s)
        # shifting angle
        sh = sigma - f - .5*numpy.pi
        rOrb = p/(1.0+e*cos(s))
#        print("rOrb =",rOrb)
        xOrb = rOrb * cos(-s-sh)
        yOrb = rOrb * sin(-s-sh) - R
        plt.plot(xOrb,yOrb,'g--')

        # Draw orbit injection point
        r0 = p/(1.0+e*cos(f))
#        print("r0 =",r0)
        x0 = r0 * cos(-f-sh)
        y0 = r0 * sin(-f-sh) - R
        plt.plot(x0,y0,'og')

        # Plot trajectory in default color (blue)
        plt.plot(X,Z)
        plt.plot(X[0],Z[0],'ok')

        # Plot burning segments in red
        for i in range(len(indBurn)):
            ib,ish = indBurn[i],indShut[i]
            plt.plot(X[ib:ish],Z[ib:ish],'r')

        plt.grid(True)
        plt.xlabel("X [km]")
        plt.ylabel("Z [km]")
        plt.axis('equal')
        plt.title("Rocket trajectory on Earth")
        plt.show()

#
#%%
def calcXdot(sizes,t,x,u,constants,restrictions):
    n = sizes['n']
    grav_e = constants['grav_e']
    Thrust = constants['Thrust']
    Isp = constants['Isp']
    r_e = constants['r_e']
    GM = constants['GM']
    CL0 = constants['CL0']
    CL1 = constants['CL1']
    CD0 = constants['CD0']
    CD2 = constants['CD2']
    s_ref = constants['s_ref']
    DampCent = constants['DampCent']
    DampSlop = constants['DampSlop']
    #alpha_min = restrictions['alpha_min']
    #alpha_max = restrictions['alpha_max']
    #beta_min = restrictions['beta_min']
    #beta_max = restrictions['beta_max']
    sin = numpy.sin
    cos = numpy.cos

    u1 = u[0]
    u2 = u[1]

    # calculate variables alpha and beta
    alpha = u1#(alpha_max + alpha_min)/2 + tanh(u1)*(alpha_max - alpha_min)/2
    beta = u2#(beta_max + beta_min)/2 + tanh(u2)*(beta_max - beta_min)/2

    # calculate variables CL and CD
    CL = CL0 + CL1*alpha
    CD = CD0 + CD2*(alpha)**2

    # calculate L and D

    dens = rho(x[0])
    pDynTimesSref = .5 * dens * (x[1]**2) * s_ref
    L = CL * pDynTimesSref
    D = CD * pDynTimesSref

    # calculate r
    r = r_e + x[0]

    # calculate grav
    grav = GM/r/r

    # calculate phi:
    dx = numpy.empty(n)

    # example rocket single stage to orbit with Lift and Drag
    sinGama = sin(x[2])
    dx[0] = x[1] * sinGama
    dx[1] = (beta * Thrust * cos(alpha) - D)/x[3] - grav * sinGama
    dx[2] = (beta * Thrust * sin(alpha) + L)/(x[3] * x[1]) + \
            cos(x[2]) * ( x[1]/r  -  grav/x[1] )
    dx[2] *= .5*(1.0+numpy.tanh(DampSlop*(t-DampCent)))
    dx[3] = -(beta * Thrust)/(grav_e * Isp)
    #if t < 3.0:
#        print(t)
    #    dx[2] = 0.0
    return dx
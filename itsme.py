#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Apr 14 14:14:40 2017

@author: Carlos

Initial Trajectory Setup ModulE

Version 2.0
Including:
    Variable multi-stage model
    New parametric model

"""

import numpy
import configparser
import matplotlib.pyplot as plt
from scipy.integrate import ode
from atmosphere import rho

global totalTrajectorySimulationCounter
totalTrajectorySimulationCounter = 0

def itsInitialization(fileAdress):

    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(fileAdress)

    #Constants
    con = dict()

    # Enviromental constants
    section = 'enviroment'
    items = config.items(section)
    for para in items:
        con[para[0]] = config.getfloat(section,para[0])
    con['g0'] = con['GM']/(con['R']**2)            # [km/s2] gravity acceleration on earth surface

    # General constants
    con['pi'] = numpy.pi
    con['d2r'] = numpy.pi/180.0

    #Initial state constants
    con['h_initial'] = config.getfloat('initial','h')
    con['V_initial'] = config.getfloat('initial','V')
    con['gamma_initial'] = config.getfloat('initial','gamma')*con['d2r']

    #Final state constants
    con['h_final'] = config.getfloat('final','h')
    con['V_final'] = numpy.sqrt(con['GM']/(con['R']+con['h_final'])) - con['we']*(con['R']+con['h_final'])   # km/s Circular velocity
    con['gamma_final'] = config.getfloat('final','gamma')*con['d2r']

    #Vehicle parameters
    section = 'vehicle'
    items = config.items(section)
    for para in items:
        con[para[0]] = config.getfloat(section,para[0])
    con['NStag'] = config.getint('vehicle','NStag')               # Number of stages
    con['c'] = con['Isp'] * con['g0'] # km/s

    # Trajectory parameters
    section = 'trajectory'
    items = config.items(section)
    for para in items:
        con[para[0]] = config.getfloat(section,para[0])
    con['torb'] = 2*con['pi']*(con['R'] + con['h_final'])/con['V_final'] # Time of one orbit using the final velocity

    # Reference values
    iniEst = initialEstimate(con)
    con['Dv1ref'] = iniEst.dv
    con['tref'] = iniEst.t
    con['vxref'] = iniEst.vx

    # Solver parameters
    con['tol'] = config.getfloat('solver','tol')

     # Superior and inferior limits
    auxstr = config.get('solver','guess')
    auxstr = auxstr.split(',')
    auxnum = []
    for n in auxstr:
        auxnum = auxnum+[float(n)]
    guess = numpy.array(auxnum)

    auxstr = config.get('solver','limit')
    auxstr = auxstr.split(',')
    auxnum = []
    for n in auxstr:
        auxnum = auxnum+[float(n)]
    limit = numpy.array(auxnum)

    con['fsup'] = guess + limit
    con['finf'] = guess - limit

    return con

def its(*arg):

    # arguments analisys
    if len(arg) == 0:
        con = itsInitialization('default.its')
    elif len(arg) == 1:
        con = itsInitialization(arg[0])
    else:
        raise Exception('itsme saying: too many arguments on its')

    ###########################
    # initial_trajectory_setup
    fsup = con['fsup']
    finf = con['finf']
    h_final = con['h_final']
    Mu = con['Mu']
    tol = con['tol']

    factors = bisecAltitude(fsup,finf,h_final,Mu,con,tol)
    errors, tt, xx, tabAlpha, tabBeta = trajectorySimulate(factors,h_final,Mu,con,"design",tol)
    num = "8.6e"
    print("\n\####################################################")
    print("ITS the end (lol)") #mongolice... haha
    print(("Error     : %"+num+", %"+num+", %"+num) % ( errors[0], errors[1], errors[2]))
    print(("Sup limits: %"+num+", %"+num+", %"+num) % (   fsup[0],   fsup[1],   fsup[2]))
    print(("Factors   : %"+num+", %"+num+", %"+num) % (factors[0],factors[1],factors[2]))
    print(("Inf limits: %"+num+", %"+num+", %"+num) % (   finf[0],   finf[1],   finf[2]))
    tt,xx,uu,_,_,_ = trajectorySimulate(factors,h_final,Mu,con,"plot",tol)

    displayResults(factors,con['h_final'],con['Mu'],con,con['tol'])

    return factors,tt,xx,uu,tabAlpha,tabBeta

def bisecSpeedAndAng(fsup,finf,factors1,f3,h_final,Mu,con,tol):
    ####################################################################
    # Bissection speed and gamma loop

    # Initializing parameters
    # Loop initialization
    stop = False
    count = 0
    Nmax = 50

    # Fators initilization
    df = abs( (fsup - finf)/5 )
    # Making the 3 factor variarions null
    factors1[2] = f3 + 0.0
    df[2] = 0.0
    factors2 = factors1 + df
    errors1, tt, xx, _, _ = trajectorySimulate(factors1,h_final,Mu,con,"design",tol)
    step = df + 0.0
    factors3 = factors2 + 0.0

    # Loop
    while (not stop) and (count <= Nmax):

        # Error update
        errors2, _, _, _, _ = trajectorySimulate(factors2,h_final,Mu,con,"design",tol)

        converged = abs(errors2) < tol
        if converged[0] and converged[1]:
            stop = True
            # Display information
            print("\n\####################################################")
            if count == Nmax:
                print("bisecSpeedAndAng total iterations: ", count," (max)")
            else:
                print("bisecSpeedAndAng total iterations: ", count)
            num = "8.6e"
            print(("Errors    : %"+num+", %"+num) % ( errors2[0],  errors2[1]))
            print(("Sup limits: %"+num+", %"+num+", %"+num) % (    fsup[0],     fsup[1],     fsup[2]))
            print(("Factors   : %"+num+", %"+num+", %"+num) % (factors2[0], factors2[1], factors2[2]))
            print(("Inf limits: %"+num+", %"+num+", %"+num) % (    finf[0],     finf[1],     finf[2]))
        else:
            de = (errors2 - errors1)
            for ii in range(0,2):
                # Division and step check
                if de[ii] == 0:
                    step[ii] = 0
                else:
                    step[ii] = errors2[ii]*(factors2[ii] - factors1[ii])/de[ii]

                if step[ii] > df[ii]:
                    step[ii] = df[ii] + 0.0
                elif step[ii] < -df[ii]:
                    step[ii] = -df[ii] + 0.0
                # if end

                # factor check
                factors3[ii] = factors2[ii] - step[ii]

                if factors3[ii] > fsup[ii]:
                    factors3[ii] = fsup[ii] + 0.0
                elif factors3[ii] < finf[ii]:
                    factors3[ii] = finf[ii] + 0.0
                #if end

            # for end
            errors1 = errors2 + 0.0
            factors1 = factors2 + 0.0
            factors2 = factors3 + 0.0
            count += 1
        #if end
    #while end
    # Define output
    errorh = errors2[2]
    return errorh,factors2
# bisecSpeedAndAng end

def bisecAltitude(fsup,finf,h_final,Mu,con,tol):

    ##########################################################################
    # Bisection altitude loop

    # Parameters initialization
    # Loop initialization
    stop = False
    count = 0
    Nmax = 50

    # Fators initilization
    df = abs( (fsup[2] - finf[2])/5 )
    factors = (fsup + finf)/2
    step = df.copy()
    f1 = (fsup[2] + finf[2])/2
    e1,factors = bisecSpeedAndAng(fsup,finf,factors,f1,h_final,Mu,con,tol)
    f2 = f1 + step

    # Loop
    while (not stop) and (count <= Nmax):

        # bisecSpeedAndAng: Error update from speed and gamma loop
        e2,factors = bisecSpeedAndAng(fsup,finf,factors,f2,h_final,Mu,con,tol)

        # Loop checks
        if  (abs(e2) < tol):
            stop = True
            # Display final information
            num = "8.6e"
            print("\n\####################################################")
            print("bisecAltitude final iteration: ",count)
            print(("Error     : %"+num) % e2)
            print(("Sup limits: %"+num+", %"+num+", %"+num) % (   fsup[0],   fsup[1],   fsup[2]))
            print(("Factors   : %"+num+", %"+num+", %"+num) % (factors[0],factors[1],        f2))
            print(("Inf limits: %"+num+", %"+num+", %"+num) % (   finf[0],   finf[1],   finf[2]))

        else:
            # Calculation of the new factor
            # Checkings
            # Division and step check
            de = (e2 - e1)
            if abs(de) < tol*1e-2:
                step = df

            else:
                der = (f2 - f1)/de
                step = e2*der
                if step > df:
                    step = 0.0 + df
                elif step < -df:
                    step = 0.0 - df

            # Factor definition and check
            f3 = f2 - step

            if f3 > fsup[2]:
                f3 = 0.0 + fsup[2]
            elif f3 < finf[2]:
                f3 = 0.0 + finf[2]

            # Parameters update
            f1 = f2.copy()
            f2 = f3.copy()
            e1 = e2.copy()
            count += 1

            # Display information
            num = "8.6e"
            print("\n\####################################################")
            print("bisecAltitude iteration: ",count)
            print(("Error     : %"+num) % e2)
            print(("Sup limits: %"+num+", %"+num+", %"+num) % (   fsup[0],   fsup[1],   fsup[2]))
            print(("Factors   : %"+num+", %"+num+", %"+num) % (factors[0],factors[1],        f2))
            print(("Inf limits: %"+num+", %"+num+", %"+num) % (   finf[0],   finf[1],   finf[2]))
        # if end

    return factors
# bisecAltitude end

def trajectorySimulate(factors,h_final,Mu,con,typeResult,tol):

    ##########################################################################
    # Trajetory design parameters
    fdv2,ftf,fdv1 = factors

    ##########################################################################
    # Delta V estimates
    Dv1 = fdv1*con['Dv1ref']
    tf = ftf*con['tref']
    Dv2 =  con['V_final'] - fdv2*con['vxref']

    ##########################################################################
    # Staging calculation
    efes = con['efes'] # Structural efficience as defined by Cornelisse (1979)
    efflist = []
    T = []
    if con['NStag'] > 1:

        for jj in range(0,con['NStag']-1):
            efflist = efflist+[efes]
            T = T+[con['T']]

        p2 = optimalStaging([efes],Dv2,con['T'],con,Mu)
        p1 = optimalStaging(efflist,Dv1,T,con,p2.mtot[0])

    if con['NStag'] == 0 or con['NStag'] == 1:
        # This cases are similar to NStag == 2, the differences are:
        # for NStag == 0 no mass is jetsoned
        # for NStag == 1 all structural mass is jetsoned at the end of all burning
        for jj in range(0,1):
            efflist = efflist+[efes]
            T = T+[con['T']]

        p2 = optimalStaging([efes],Dv2,con['T'],con,Mu)
        p1 = optimalStaging(efflist,Dv1,T,con,p2.mtot[0])

        if con['NStag'] == 0:
            p2.me[0] = 0.0
            p1.me[0] = 0.0
        if con['NStag'] == 1:
            p2.me[0] = p1.me[0] + p2.me[0]
            p1.me[0] = 0.0

    if p1.fail or p2.fail:
        raise Exception('itsme saying: Too few stages!')

    if p1.mtot[0]*con['g0'] > T[0]:
        raise Exception('itsme saying: weight greater than thrust!')

    ##########################################################################
    # thrust program
    tabBeta = retSoftPulse(p1,p2,tf,1.0,0.0,con['softness'])
    if tabBeta.fail:
        raise Exception('itsme saying: Softness too high!')

    ##########################################################################
    # Attitude program definition
    tAoA2 = con['tAoA1'] + con['tAoA']
    tabAlpha = cosSoftPulse(con['tAoA1'],tAoA2,0,-con['AoAmax']*con['d2r'])

    ##########################################################################
    #Integration

    # initial conditions
    t0 = 0.0
    x0 = numpy.array([con['h_initial'],con['V_initial'],con['gamma_initial'],p1.mtot[0]])

    # Integrator setting
    # ode set:
    #         atol: absolute tolerance
    #         rtol: relative tolerance
    ode45 = ode(mdlDer).set_integrator('dopri5',nsteps=1,atol = tol/1,rtol = tol/10)
    ode45.set_initial_value(x0, t0).set_f_params((tabAlpha,tabBeta,con))

    # Phase times, incluiding the initial time in the begining
    tphases   = [ t0,con['tAoA1'],tAoA2]+tabBeta.tflist
    mjetsoned = [0.0,         0.0,  0.0]+tabBeta.melist
    if (typeResult == "orbital"):
        tphases   =   tphases+[con['torb']]
        mjetsoned = mjetsoned+[        0.0]

    # Integration using rk45 separated by phases
    # Automatic multiphase integration
    if (typeResult == "design"):
        # Light running
        tt,xx,tp,xp = totalIntegration(tphases,mjetsoned,ode45,t0,x0,False)
        h,v,gamma,M = xx
        errors = ((v - con['V_final'])/0.01, (gamma - con['gamma_final'])/0.1, (h - h_final)/10)
        errors = numpy.array(errors)
        ans = errors, tt, xx, tabAlpha, tabBeta

    elif (typeResult == "plot") or (typeResult == "orbital"):
        print("\n\rInitial Stages:")
        p1.printInfo()
        print("\n\rFinal Stage:")
        p2.printInfo()

        tt,xx,tp,xp = totalIntegration(tphases,mjetsoned,ode45,t0,x0,True)
        uu = numpy.concatenate([tabAlpha.multValue(tt),tabBeta.multValue(tt)], axis=1)
        up = numpy.concatenate([tabAlpha.multValue(tp),tabBeta.multValue(tp)], axis=1)
        ans = (tt,xx,uu,tp,xp,up)

    return ans

def totalIntegration(tphases,mjetsoned,ode45,t0,x0,flagAppend):

    global totalTrajectorySimulationCounter
    Nref = 20.0 # Number of interval divisions for determine first step
    # Output variables
    tt,xx,tp,xp = [t0],[x0],[t0],[x0]

    for ii in range(1,len(tphases)):
        tt,xx,tp,xp = phaseIntegration(tphases[ii - 1],tphases[ii],mjetsoned[ii-1],Nref,ode45,tt,xx,tp,xp,flagAppend)
        if flagAppend:
            if ii == 1:
                print("Phase integration iteration:1",end=', '),
            elif ii == (len(tphases) - 1):
                print('')
            else:
                print(ii,end=', ')

    tt = numpy.array(tt)
    xx = numpy.array(xx)
    tp = numpy.array(tp)
    xp = numpy.array(xp)

    totalTrajectorySimulationCounter += 1

    return tt,xx,tp,xp

def phaseIntegration(t_initial,t_final,mj,Nref,ode45,tt,xx,tp,xp,flagAppend):

    ode45.first_step = (t_final - t_initial)/Nref
    ode45.y[3] = ode45.y[3] - mj
    while ode45.t < t_final:
        ode45.integrate(t_final)
        if flagAppend:
            tt.append(ode45.t)
            xx.append(ode45.y)

    ode45.integrate(t_final)

    if flagAppend:
        tt.append(ode45.t)
        xx.append(ode45.y)
        tp.append(ode45.t)
        xp.append(ode45.y)
        tt[-1] = tt[-1] + numpy.finfo(float).eps*100 # avoinding coincident points
    else:
        tt = ode45.t
        xx = ode45.y

    return tt,xx,tp,xp


def plotResults(tt,xx,uu,tp,xp,up,con):

    ii = 0
    plt.subplot2grid((6,4),(0,0),rowspan=2,colspan=2)
    plt.hold(True)
    plt.plot(tt,xx[:,ii],'.-b')
    plt.plot(tp,xp[:,ii],'.r')
    plt.hold(False)
    plt.grid(True)
    plt.ylabel("h [km]")

    ii = 1
    plt.subplot2grid((6,4),(0,2),rowspan=2,colspan=2)
    plt.hold(True)
    plt.plot(tt,xx[:,ii],'.-b')
    plt.plot(tp,xp[:,ii],'.r')
    plt.hold(False)
    plt.grid(True)
    plt.ylabel("V [km/s]")

    ii = 2
    plt.subplot2grid((6,4),(2,0),rowspan=2,colspan=2)
    plt.hold(True)
    plt.plot(tt,xx[:,ii]*180.0/numpy.pi,'.-b')
    plt.plot(tp,xp[:,ii]*180.0/numpy.pi,'.r')
    plt.hold(False)
    plt.grid(True)
    plt.ylabel("gamma [deg]")

    ii = 3
    plt.subplot2grid((6,4),(2,2),rowspan=2,colspan=2)
    plt.hold(True)
    plt.plot(tt,xx[:,ii],'.-b')
    plt.plot(tp,xp[:,ii],'.r')
    plt.hold(False)
    plt.grid(True)
    plt.ylabel("m [kg]")

    ii = 0
    plt.subplot2grid((6,4),(4,0),rowspan=2,colspan=2)
    plt.hold(True)
    plt.plot(tt,uu[:,ii]*180/numpy.pi,'.-b')
    plt.plot(tp,up[:,ii]*180/numpy.pi,'.r')
    plt.hold(False)
    plt.grid(True)
    plt.ylabel("alfa [deg]")

    ii = 1
    plt.subplot2grid((6,4),(4,2),rowspan=2,colspan=2)
    plt.hold(True)
    plt.plot(tt,uu[:,ii],'.-b')
    plt.plot(tp,up[:,ii],'.r')
    plt.hold(False)
    plt.grid(True)
    plt.xlabel("t")
    plt.ylabel("beta [adim]")

    plt.show()

#    # Aed plots
#    LL, DD, CCL, CCD, QQ = calcAedTab(tt,xx,uu,con)
#
#    ii = 0
#    plt.subplot2grid((6,2),(0,0),rowspan=2,colspan=2)
#    plt.hold(True)
#    plt.plot(tt,LL,'.-b')
#    plt.plot(tt,DD,'.-r')
#    plt.hold(False)
#    plt.grid(True)
#    plt.ylabel("L and D [kN]")
#
#    ii = 1
#    plt.subplot2grid((6,2),(2,0),rowspan=2,colspan=2)
#    plt.hold(True)
#    plt.plot(tt,CCL,'.-b')
#    plt.plot(tt,CCD,'.-r')
#    plt.hold(False)
#    plt.grid(True)
#    plt.ylabel("CL and CD [-]")
#
#    ii = 2
#    plt.subplot2grid((6,2),(4,0),rowspan=2,colspan=2)
#    plt.hold(True)
#    plt.plot(tt,QQ,'.-b')
#    plt.hold(False)
#    plt.grid(True)
#    plt.ylabel("qdin [kPa]")
#
#
#    plt.show()

    return None

def displayResults(factors,h_final,Mu,con,tol):

    # Results without orbital phase
    tt0,xx0,uu0,tp0,xp0,up0 = trajectorySimulate(factors,h_final,Mu,con,"plot",tol)
    h,v,gama,M = numpy.transpose(xx0[-1,:])
    eec = orbitResults(h,v,gama,con)
    plotResults(tt0,xx0,uu0,tp0,xp0,up0,con)

    # Results with orbital phase
    if abs(eec-1) > 0.1:
        # The eccentricity test avoids simulations too close of the singularity
        tt0,xx0,uu0,tp0,xp0,up0 = trajectorySimulate(factors,h_final,Mu,con,"orbital",tol)
        h,v,gama,M = numpy.transpose(xx0[-1,:])
        orbitResults(h,v,gama,con)
        plotResults(tt0,xx0,uu0,tp0,xp0,up0,con)

    print('Initial states:',xx0[ 0])
    print('Final   states:',xx0[-1])

    return None

def orbitResults(h,v,gama,con):

    GM = con['GM']       # km^3 s^-2
    R = con['R']               # km

    r = R + h
    cosGama = numpy.cos(gama)
    sinGama = numpy.sin(gama)
    momAng = r * v * cosGama
    print("Ang mom:",momAng)
    en = .5 * v * v - GM/r
    print("Energy:",en)
    a = - .5*GM/en
    print("Semi-major axis:",a)
    aux = v * momAng / GM
    e = numpy.sqrt((aux * cosGama - 1)**2 + (aux * sinGama)**2)
    print("Eccentricity:",e)

    print("Final altitude:",h)
    ph = a * (1.0 - e) - R
    print("Perigee altitude:",ph)
    ah = 2*(a - R) - ph
    print("Apogee altitude:",ah)

    return e


def mdlDer(t,x,arg):

    h,v,gama,M = x[0],x[1],x[2],x[3]
    alfaProg,betaProg,con = arg
    T = con['T']
    Isp = con['Isp']
    g0 = con['g0']
    R = con['R']
    betat = betaProg.value(t)
    alfat = alfaProg.value(t)

    btm = betat*T/M
    sinGama = numpy.sin(gama)
    g = g0*(R/(R+h))**2 - (con['we']**2)*(R + h)

# Aerodynamics
    if numpy.isnan(h):
       raise Exception('itsme saying: h is not a number')
    L,D,_,_,_ = aed(h,v,alfat,con)

    return numpy.array([v*sinGama,\
    btm*numpy.cos(alfat) - g*sinGama - (D/M),\
    btm*numpy.sin(alfat)/v + (v/(h+R)-g/v)*numpy.cos(gama) + (L/(v*M)) + 2*con['we'],\
    -btm*M/g0/Isp])

def aed(h,v,alfat,con):
    CL = con['CL0'] + con['CL1']*alfat
    CD = con['CD0'] + con['CD2']*(alfat**2)

    qdin = 0.5 * rho(h) * (v**2)
    L = qdin * con['s_ref'] * CL
    D = qdin * con['s_ref'] * CD

    return L,D,CL,CD,qdin

def calcAedTab(tt,xx,uu,con):

    LL = tt.copy()
    DD = tt.copy()
    CCL = tt.copy()
    CCD = tt.copy()
    QQ = tt.copy()
    for ii in range( 0, len(tt) ):
        L,D,CL,CD,qdin = aed(xx[ii,0],xx[ii,1],uu[ii,0],con)
        LL[ii] = L
        DD[ii] = D
        CCL[ii] = CL
        CCD[ii] = CD
        QQ[ii] = qdin

    return LL, DD, CCL, CCD, QQ


class retPulse():

    def __init__(self,t1,t2,v1,v2):
        self.t1 = t1
        self.t2 = t2
        self.v1 = v1
        self.v2 = v2

    def value(self,t):
        if (t < self.t1):
            return self.v1
        elif (t < self.t2):
            return self.v2
        else:
            return self.v1

    def multValue(self,t):
        N = len(t)
        ans = numpy.full((N,1),self.v1)
        for ii in range(0,N):
            if (t[ii] >= self.t1) and (t[ii] < self.t2):
                ans[ii] = self.v2
        return ans

class retSoftPulse():

    def __init__(self,p1,p2,tf,v1,v2,softness):
        self.t1 = p1.tf[-1]
        self.t2 = tf - p2.tb[-1]
        self.t3 = tf

        self.v1 = v1
        self.v2 = v2

        self.f = softness/2

        self.d1  = self.t1 # width of retangular and 0.5 soft part
        self.c1  = self.d1*self.f # width of the 0.5 soft part
        self.fr1  = self.d1 - self.c1 # final of the retangular part
        self.fs1  = self.d1 + self.c1 # final of the retangular part

        self.d2  = self.t3 - self.t2 # width of retangular and 0.5 soft part
        self.c2  = self.d2*self.f # width of the 0.5 soft part
        self.r2  = self.d2 - self.c2 # width of the retangular part
        self.ir2 = self.t2 + self.c2 # start of the retangular part
        self.is2 = self.t2 - self.c2 # start of the soft part

        self.dv21 = v2 - v1

        # List of time events and jetsoned masses
        self.tflist = p1.tf[0:-1].tolist()+[self.fr1,  self.fs1]+[self.is2,self.ir2,        tf]
        self.melist = p1.me[0:-1].tolist()+[     0.0, p1.me[-1]]+[    0.0,      0.0, p2.me[-1]]

        self.fail = False
        if len(p1.tf) > 2:
            if p1.tf[-2] >= self.fr1:
                self.fail = True

    def value(self,t):
        if (t <= self.fr1):
            return self.v1
        elif (t <= self.fs1):
            cos = numpy.cos( numpy.pi*(t - self.fr1)/(2*self.c1) )
            return self.dv21*(1 - cos)/2 + self.v1
        elif (t <= self.is2):
            return self.v2
        elif (t <= self.ir2):
            cos = numpy.cos( numpy.pi*(t - self.is2)/(2*self.c2) )
            return -self.dv21*(1 - cos)/2 + self.v2
        elif (t <= self.t3):
            return self.v1
        else:
            return 0.0

    def multValue(self,t):
        N = len(t)
        ans = numpy.full((N,1),0.0)
        for jj in range(0,N):
            ans[jj] = self.value(t[jj])

        return ans

class cosSoftPulse():

    def __init__(self,t1,t2,v1,v2):
        self.t1 = t1
        self.t2 = t2

        self.v1 = v1
        self.v2 = v2

    def value(self,t):
        if (t >= self.t1) and (t <= self.t2):
            ans = (self.v2 - self.v1) * (1 - numpy.cos(2*numpy.pi * (t - self.t1)  / (self.t2 - self.t1))) / 2 + self.v1
            return ans
        else:
            return self.v1

    def multValue(self,t):
        N = len(t)
        ans = numpy.full((N,1),0.0)
        for jj in range(0,N):
            ans[jj] = self.value(t[jj])

        return ans


class retPulse2():

    def __init__(self,tVec,vVec):
        self.tVec = tVec
        self.vVec = vVec

    def value(self,t):
        ii = 0
        NVec = len(self.tVec)
        stop = False
        while not stop:
            if (t <= self.tVec[ii]):
                ans = self.vVec[ii]
                stop = True
            else:
                ii = ii + 1
                if ii == NVec:
                    ans = self.vVec[-1]
                    stop = True

        return ans

    def multValue(self,t):
        N = len(t)
        ans = numpy.full((N,1),self.vVec[0])
        for jj in range(0,N):
            ans[jj] = self.value(t[jj])

        return ans

class optimalStaging():
    # optimalStaging() returns a object with information of optimal staging factor
    # The maximal staging reason is defined as reducing the total mass for a defined
    # delta V.
    # Structural eficience and thrust shall variate for diferent stages, but
    # specific impulse must be the same for all stages
    # Based in Cornelisse (1979)

    def __init__(self,effList,dV,T,con,mu):
        self.e = numpy.array(effList)
        self.T = numpy.array(T)
        self.dV = dV
        self.mu = mu
        self.c = con['Isp']*con['g0']
        self.mflux = self.T/self.c
        self.mE = self.calcGeoMeanE()
        self.m1E = self.calcGeoMean1E()
        self.fail = False
        self.lamb = self.calc_lamb()
        self.phi = (1 - self.e)*(1 - self.lamb)

        self.mtot = self.calc_mtot()             # Total sub-rocket mass
        self.mp = self.mtot*self.phi             # Propelant mass on each stage
        self.me = self.mp*(self.e/(1 - self.e))  # Strutural mass of each stage
        self.tb = self.mp/self.mflux             # Duration of each stage burning
        self.tf = self.calc_tf()                 # Final burning time of each stage

    def calcGeoMeanE(self):

        a = self.e
        m = 1.0
        for v in a:
            m = m*v
        m = m ** (1/a.size)
        return m

    def calcGeoMean1E(self):

        a = 1 - self.e
        m = 1.0
        for v in a:
            m = m*v
        m = m ** (1/a.size)
        return m

    def calc_lamb(self):

        LtN = ( numpy.exp(-self.dV/(self.c*self.e.size)) - self.mE)/self.m1E
        self.LtN = LtN

        if LtN <= 0:
            self.fail = True

        lamb = (self.e/(1 - self.e))*(LtN*self.m1E/self.mE)
        return lamb

    def calc_mtot(self):

        mtot = self.e*0.0
        N = self.e.size-1
        for ii in range(0,N+1):
            if ii == 0:
                mtot[N - ii] = self.mu/self.lamb[N - ii]
            else:
                mtot[N - ii] = mtot[N - ii + 1]/self.lamb[N - ii]
        return mtot

    def calc_tf(self):

        tf = self.e*0.0
        N = self.tb.size-1
        for ii in range(0,N+1):
            if ii == 0:
                tf[ii] = self.tb[ii]
            else:
                tf[ii] = self.tb[ii] + tf[ii-1]
        return tf

    def printInfo(self):

        print("dV =",self.dV)
        print("mu =",self.mu)
        print("mp =",self.mp)
        print("me =",self.me)
        print("mtot =",self.mtot)
        print("tf =",self.tf,"\n\r")

class initialEstimate():

    def __init__(self,con):
#        dd = numpy.exp(-0.5*con['V_final']/con['c']) - con['efes']
#        if dd < 0.1:
#            dd = 0.0
#        lamb = dd/(1 - con['efes'])

        lamb = numpy.exp(0.5*con['V_final']/con['c'])
        self.Mu = con['Mu']*lamb
        self.hf = con['h_final']
        self.M0max = con['T']/con['g0']
        self.mflux = con['T']/con['c']
        self.GM = con['GM']
        self.R = con['R']
        self.c = con['c']
        self.e = con['efes']
        self.g0 = con['g0']
        self.t1max = self.M0max/self.mflux
        self.fail = False

        self.calculate()

        self.vx = 0.5*self.V1*(con['R'] + self.h1)/(con['R']+self.hf)

    def newRap(self):

        N = 100
        t1max = self.t1max

        dt = t1max/N
        t1 = 0.1*t1max

        cont = 0
        erro = 1.0

        while (abs(erro) > 1e-6) and not self.fail:

            erro = self.hEstimate(t1) - self.hf
            dedt = (self.hEstimate(t1+dt) - self.hEstimate(t1-dt))/(2*dt)
            t1 = t1 - erro/dedt
            cont += 1
            if cont == 100:
                raise Exception('itsme saying: initialEstimate failed')

        self.cont = cont
        self.t1 = t1
        return None

    def hEstimate(self,t1):

        mflux = self.mflux
        Mu = self.Mu
        g0 = self.g0
        c = self.c

        Mp = mflux*t1
        Me = Mp*self.e/(1 - self.e)
        M0 = Mu + Me + Mp
        x = (Mu + Me)/M0
        V1 = c*numpy.log(1/x) - g0*t1
        h1 = (c*M0/mflux) * ( (x*numpy.log(x) -x ) + 1) - g0*(t1**2)/2
        h = h1 + self.GM/(self.GM/(self.R + h1) - (V1**2)/2) - self.R

        return h

    def dvt(self):

        t1 = self.t1
        mflux = self.mflux
        Mu = self.Mu
        g0 = self.g0
        c = self.c

        M0 = Mu + mflux*t1
        V1 = c*numpy.log(M0/Mu) - g0*t1
        dv = V1 + g0*t1
        x = Mu/M0
        h1 = (c*M0/mflux) * ( (x*numpy.log(x) -x ) + 1) - g0*(t1**2)/2

        h = self.hEstimate(self.t1)

        rr = (self.R + h1)/(self.R + h)
        if rr > 1:
            raise Exception('itsme saying: initialEstimate failed (h1 > h)')
        theta = numpy.arccos( numpy.sqrt( rr ) )
        ve = numpy.sqrt(2*self.GM/(self.R + h))

        t = t1 + ( (self.R + h)/ve ) * ( numpy.sin(2*theta)/2 + theta )

        self.h1 = h1
        self.h = h
        self.t = t
        self.dv = dv
        self.V1 = V1

        return None

    def calculate(self):

        self.newRap()
        self.dvt()

        return None


if __name__ == "__main__":

    print("itsme: Inital Trajectory Setup Module")

    ################
    #    Errors:

    #    (v - V_final)/0.01
    #    (gamma - gamma_final)/0.1
    #    (h - h_final)/10


    ################
    # Initital display of vehicle trajectory
    con = itsInitialization('default.its')
    factors = (con['fsup'] + con['finf'])/2
    displayResults(factors,con['h_final'],con['Mu'],con,con['tol'])

    # Factor adjustment
    new_factors,_,_,_,tabAlpha,tabBeta = its()

    # Results with automatic adjustment

    print("\n\rTotal number of trajectory simulations", totalTrajectorySimulationCounter)
    #input("Press any key to finish...")

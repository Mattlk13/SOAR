# -*- coding: utf-8 -*-
"""
Created on Wed Jan 18 14:02:30 2017

@author: munizlgmn
"""

import numpy

# ##################
# PROBLEM DOMAIN:
# ##################
def declProb():
# time discretization    
    N = 5000 + 1    
    dt = 1.0/(N-1)
    t = numpy.arange(0,1.0+dt,dt)
    
# example rocket single stage to orbit L=0 D=0

# state condition
    h_initial = 0.0            # km  
    V_initial = 0.0            # km/s
    gamma_initial = numpy.pi/2 # rad
    m_initial = 50000          # kg
    h_final = 463              # km
    V_final = 7.633            # km/s    
    gamma_final = 0.0          # rad
    #m_final = free            # kg

# matrix sizes    
    n = 4
    m = 2
    p = 1 
    q = 3  # 3 (Miele 1970)  # 7 (Miele 2003)     

# Earth constants   
    grav_e = 9.8e-3        # km/s^2
    r_e = 6371             # km
    GM = 398600.4415       # km^3 s^-2 

# rocket constants    
    Thrust = 1.3*m_initial*grav_e # N
    Isp = 450              # s
    s_f = 0.05

# prepare state
    state = dict()
    state['h_initial'] = h_initial
    state['V_initial'] = V_initial
    state['gamma_initial'] = gamma_initial
    state['m_initial'] = m_initial
    state['h_final'] = h_final
    state['V_final'] = V_final
    state['gamma_final'] = gamma_final
    
# prepare sizes
    sizes = dict()
    sizes['N'] = N
    sizes['n'] = n
    sizes['m'] = m
    sizes['p'] = p 
    sizes['q'] = q

# prepare constants
    constants = dict()
    constants['grav_e'] = grav_e
    constants['Thrust'] = Thrust
    constants['Isp'] = Isp
    constants['r_e'] = r_e
    constants['GM'] = GM
    constants['s_f'] = s_f

# initial guess:

# example rocket single stage to orbit L=0 D=0
    x = numpy.zeros((N,n))
    x[:,0] = h_final*numpy.sin(numpy.pi*t.copy()/2)
    x[:,1] = 3.793*numpy.exp(0.7256*t) -1.585 -3.661*numpy.cos(3.785*t+0.9552)
    #x[:,1] = V_final*numpy.sin(numpy.pi*t.copy()/2)
    #x[:,1] = 1.0e3*(-0.4523*t.copy()**5 + 1.2353*t.copy()**4-1.1884*t.copy()**3+0.4527*t.copy()**2-0.0397*t.copy())
    x[:,2] = (numpy.pi/2)*(numpy.exp(-(t.copy()**2)/0.017))+0.06419
    x[:,3] = m_initial*((0.7979*numpy.exp(-(t.copy()**2)/0.02))+0.1901*numpy.cos(t.copy()))
    #x[:,3] = m_initial*(1.0-0.89*t.copy())
    #x[:,3] = m_initial*(-2.9*t.copy()**3 + 6.2*t.copy()**2 - 4.2*t.copy() + 1)
   
    u = numpy.zeros((N,m))
    for k in range(N):
        if k<910:
            u[k,1] = 1.0
        else:
            if k>4999:
                u[k,1] = 0.27

    lam = 0.0*x.copy()
    mu = numpy.zeros(q)
    pi = 1100*numpy.ones((p,1))

    tol = dict()
    tol['P'] = 1.0e-8
    tol['Q'] = 1.0e-5

    return sizes,t,x,u,pi,lam,mu,tol,constants,state
    
    
#def calcR(sizes,x,constants):
#    N = sizes['N']
#    r_e = constants['r_e']
#
#    # calculate r
#    r = numpy.empty(N)
#    for k in range(N):
#        r[k] = r_e + x[k,0]
#
#    return r
    
#def calcGrav(sizes,r,constants):
#    N = sizes['N']
#    GM = constants['GM']
#
#    # calculate grav
#    grav = numpy.empty(N)
#    for k in range(N):
#        grav[k] = GM/(r[k]**2)   
#    
#    return grav
    
def calcPhi(sizes,x,u,pi,constants):
    N = sizes['N']
    n = sizes['n']
    grav_e = constants['grav_e']
    Thrust = constants['Thrust']
    Isp = constants['Isp']
    r_e = constants['r_e']
    GM = constants['GM']

# calculate r
    r = r_e + x[:,0]
    #r = numpy.empty(N)
    #for k in range(N):
    #    r[k] = r_e + x[k,0]
    
# calculate grav
    grav = GM/r/r
    #grav = numpy.empty(N)
    #for k in range(N):
    #    grav[k] = GM/(r[k]**2)
        
# calculate phi:
    phi = numpy.empty((N,n))
    
# example rocket single stage to orbit L=0 D=0     
    phi[:,0] = pi[0] * x[:,1] * numpy.sin(x[:,2])
    phi[:,1] = pi[0] * ((u[:,1] * Thrust * numpy.cos(u[:,0]))/(x[:,3]) - grav * numpy.sin(x[:,2]))
    for k in range(N):
        if k==0:
            phi[k,2] = 0.0
        else:
            phi[k,2] = pi[0] * ((u[k,1] * Thrust * numpy.sin(u[k,0]))/(x[k,3] * x[k,1]) + numpy.cos(x[k,2]) * ((x[k,1]/r[k]) - (grav[k]/x[k,1])))
    phi[:,3] = - (pi[0] * u[:,1] * Thrust)/(grav_e * Isp)    
   
    return phi
    
def calcPsi(sizes,x,state):    
    N = sizes['N']
    h_final = state['h_final']
    V_final = state['V_final']
    gamma_final = state['gamma_final']
  
# example rocket single stage to orbit L=0 D=0
    psi = numpy.array([x[N-1,0]-h_final,x[N-1,1]-V_final,x[N-1,2]-gamma_final])

    return psi
    
def calcF(sizes,x,u,pi,constants):
    N = sizes['N']
    f = numpy.empty(N)
    grav_e = constants['grav_e']
    Thrust = constants['Thrust']
    Isp = constants['Isp']
    s_f = constants['s_f']
    
    for k in range(N):
# example rocket single stage to orbit L=0 D=0
        f[k] = ((Thrust * pi[0])/(grav_e * (1-s_f) * Isp)) * u[k,1]
   
    return f

def calcGrads(sizes,x,u,pi,constants):
    Grads = dict()
        
    N = sizes['N']
    n = sizes['n']
    m = sizes['m']
    p = sizes['p']
    #q = sizes['q']
    
    grav_e = constants['grav_e']
    Thrust = constants['Thrust']
    Isp = constants['Isp']
    r_e = constants['r_e']
    GM = constants['GM']
    s_f = constants['s_f']
    
    Grads['dt'] = 1.0/(N-1)

    phix = numpy.zeros((N,n,n))
    phiu = numpy.zeros((N,n,m))
                    
    if p>0:
        phip = numpy.zeros((N,n,p))
    else:
        phip = numpy.zeros((N,n,1))

    fx = numpy.zeros((N,n))
    fu = numpy.zeros((N,m))
    fp = numpy.zeros((N,p))
    
           
    # Gradients from example rocket single stage to orbit L=0 D=0
    psix = numpy.array([[1.0,0.0,0.0,0.0],[0.0,1.0,0.0,0.0],[0.0,0.0,1.0,0.0]])        
    psip = numpy.array([[0.0],[0.0],[0.0]])
    
    # calculate r
    r = r_e + x[:,0]
    #r = numpy.empty(N)
    #for k in range(N):
    #    r[k] = r_e + x[k,0]
        
    # calculate grav
    grav = GM/r/r
    #grav = numpy.empty(N)
    #for k in range(N):
    #    grav[k] = GM/(r[k]**2)
        
    for k in range(N):
#       
    # Expanded notation:
        if k==0:
            phix[k,:,:] = numpy.array([[0.0                                                              ,pi[0]*numpy.sin(x[k,2])                                                                                     ,pi[0]*x[k,1]*numpy.cos(x[k,2])                         ,0.0                                               ],
                                       [pi[0]*2*GM*numpy.sin(x[k,2])/(r[k]**3)                           ,0.0                                                                                                         ,-pi[0]*grav[k]*numpy.cos(x[k,2])                       ,-pi[0]*u[k,1]*Thrust*numpy.cos(u[k,0])/(x[k,3]**2)],
                                       [0.0                                                              ,0.0                                                                                                         ,0.0                                                    ,0.0                                               ],
                                       [0.0                                                              ,0.0                                                                                                         ,0.0                                                    ,0.0                                               ]])
            
            phiu[k,:,:] = numpy.array([[0.0                                                    ,0.0                                    ],
                                       [-pi[0]*u[k,1]*Thrust*numpy.sin(u[k,0])/(x[k,3])        ,pi[0]*Thrust*numpy.cos(u[k,0])/(x[k,3])],
                                       [0.0                                                    ,0.0                                    ],
                                       [0.0                                                    ,-pi[0]*Thrust/(grav_e*Isp)             ]])
            
            phip[k,:,:] = numpy.array([[x[k,1]*numpy.sin(x[k,2])                                                ],
                                       [u[k,1]*Thrust*numpy.cos(u[k,0])/(x[k,3]) - grav[k]*numpy.sin(x[k,2])    ],
                                       [0.0                                                                     ],
                                       [-(u[k,1]*Thrust)/(grav_e*Isp)                                           ]])
        else:
            phix[k,:,:] = numpy.array([[0.0                                                                  ,pi[0]*numpy.sin(x[k,2])                                                                                            ,pi[0]*x[k,1]*numpy.cos(x[k,2])                                 ,0.0                                                        ],
                                       [pi[0]*2*GM*numpy.sin(x[k,2])/(r[k]**3)                               ,0.0                                                                                                                ,-pi[0]*grav[k]*numpy.cos(x[k,2])                               ,-pi[0]*u[k,1]*Thrust*numpy.cos(u[k,0])/(x[k,3]**2)         ],
                                       [-pi[0]*numpy.cos(x[k,2])*(x[k,1]/(r[k]**2) + 2*GM/(x[k,1]*(r[k]**3))),pi[0]*(-u[k,1]*Thrust*numpy.sin(u[k,0])/(x[k,3]*x[k,1]**2)+numpy.cos(x[k,2])*((1/r[k])+grav[k]/(x[k,1]**2)))       ,-pi[0]*numpy.sin(x[k,2])*((x[k,1]/r[k])-grav[k]/x[k,1])        ,-pi[0]*u[k,1]*Thrust*numpy.sin(u[k,0])/(x[k,1]*(x[k,3]**2))],
                                       [0.0                                                                  ,0.0                                                                                                                ,0.0                                                            ,0.0                                                        ]])
        
            phiu[k,:,:] = numpy.array([[0.0                                                    ,0.0                                           ],
                                       [-pi[0]*u[k,1]*Thrust*numpy.sin(u[k,0])/(x[k,3])        ,pi[0]*Thrust*numpy.cos(u[k,0])/(x[k,3])       ],
                                       [pi[0]*u[k,1]*Thrust*numpy.cos(u[k,0])/(x[k,3]*x[k,1])  ,pi[0]*Thrust*numpy.sin(u[k,0])/(x[k,3]*x[k,1])],
                                       [0.0                                                    ,-pi[0]*Thrust/(grav_e*Isp)                    ]])
            
            phip[k,:,:] = numpy.array([[x[k,1]*numpy.sin(x[k,2])                                                                            ],
                                       [u[k,1]*Thrust*numpy.cos(u[k,0])/(x[k,3]) - grav[k]*numpy.sin(x[k,2])                                ],
                                       [(u[k,1]*Thrust*numpy.sin(u[k,0]))/(x[k,3]*x[k,1])+numpy.cos(x[k,2])*((x[k,1]/r[k])-(grav[k]/x[k,1]))],
                                       [-(u[k,1]*Thrust)/(grav_e*Isp)                                                                       ]])
   
        fu[k,:] = numpy.array([0.0,(pi[0]*Thrust)/(grav_e * Isp * (1-s_f))])
        fp[k,0] =(Thrust * u[k,1])/(grav_e * Isp * (1-s_f))
    
    Grads['phix'] = phix.copy()
    Grads['phiu'] = phiu.copy()
    Grads['phip'] = phip.copy()
    Grads['fx'] = fx.copy()
    Grads['fu'] = fu.copy()
    Grads['fp'] = fp.copy()
#    Grads['gx'] = gx.copy()
#    Grads['gp'] = gp.copy()
    Grads['psix'] = psix.copy()
    Grads['psip'] = psip.copy()        
    
    return Grads
    

def calcI(sizes,x,u,pi,constants):
# example rocket single stage to orbit L=0 D=0
    f = calcF(sizes,x,u,pi,constants)
    I = f.sum()
    
    return I

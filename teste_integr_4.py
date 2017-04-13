# -*- coding: utf-8 -*-
"""
Created on Sun Apr  2 18:00:56 2017

@author: Carlos Souza
"""

import numpy
import matplotlib.pyplot as plt
from scipy.integrate import odeint
#from numpy.linalg import norm
from utils import interpV#, interpM, ddt

def main ():
	N = 5000 + 1
	dt = 7.0e-4#1.0/(N-1)
	pi = numpy.pi

	# example rocket single stage to orbit L=0 D=0
	# initial state condition
	h_initial = 0.0            # km
	V_initial = 0.0            # km/s
	gamma_initial = pi/2 # rad
	m_initial = 50000          # kg
	# final state condition
	h_final = 463     # km
	V_final = 7.633   # km/s
	gamma_final = 0.0 # rad
	GM = 398600.4415       # km^3 s^-2
	Isp = 450              # s
	efes = .95
	R = 6371             # km
	g0 = 9.8e-3
	AoAmax = 2.0 # graus

	##########################################################################
	fator_V = 1.06 # Ajust to find a final V
	tf = 480.0 # Ajust to find a final gamma
	tAoA = 0.5 #Ajust to find a final h
	fdv1 = 1.4 #Ajust to find a final h

	Mu = 100.0
	Dv1 = fdv1*numpy.sqrt(2.0*GM*(1/R - 1/(R+h_final)))
	Dv2 = V_final

	##########################################################################
	Dv2 = Dv2*fator_V
	LamMax = 1/(1-efes)
	Lam1 = numpy.exp(Dv1/g0/Isp)
	Lam2 = numpy.exp(Dv2/g0/Isp)
	print("Dv =",Dv1,"Dv =",Dv2," Lam1 =",Lam1," Lam2 =",Lam2,"LamMax =",LamMax)

	Mp2 = (Lam2-1)*efes*Mu/(1 - Lam2*(1-efes))
	Mp1 = (Lam1-1)*efes*(Mu + (Mp2/efes))/(1 - Lam1*(1-efes))
	Mp = Mp1 + Mp2;
	Me = (1-efes)*Mp/efes
	M0 = Mu + Mp + Me
	print("Mu =",Mu," Mp =",Mp," Me =",Me,"M0 =",M0)


	T = 40.0e3 # thrust in N
	T *= 1.0e-3 # thrust in kg * km / s^2 [for compatibility purposes...]

	tb1 = Mp1 * g0 * Isp / T
	tb2 = Mp2 * g0 * Isp / T
	tb = tb1 + tb2

	t = numpy.arange(0,tf+dt,dt)
	Nt = numpy.size(t)

	beta = numpy.zeros((Nt,1))
	tvar = 0.0
	i = 0
	while tvar <= tf:
		if tvar < tb1:
			beta[i] = 1#1.0
		elif tvar > (tf - tb2):
			beta[i] = 1#1.0
		i += 1
		tvar += dt

	alfa = numpy.zeros((Nt,1))
	tvar = 0.0

	##########################################################################
	# Chossing tAoA1 as a fraction of tf results in code bad behavior
	# So a fixed generic number is used
	tAoA1 = .01*440

	##########################################################################
	tAoA2 = tAoA1 + tAoA
	for i in range(Nt):
		tvar += dt
		if tvar > tAoA1 and tvar < tAoA2:
			alfa[i] = -AoAmax*pi/180#-21*pi/180


	plt.plot(t,alfa*180/pi)
	plt.grid(True)
	plt.xlabel("Time [s]")
	plt.ylabel("Angle of attack [deg]")
	plt.show()

	plt.plot(t,beta)
	plt.grid(True)
	plt.xlabel("Time [s]")
	plt.ylabel("Thrust profile [-]")
	plt.show()

	x0 = numpy.array([0,1.0e-6,90*pi/180,M0])
	x = odeint(mdlDer,x0,t,args=(t,alfa,beta,T,Isp,g0,R))

	plt.subplot2grid((6,4),(0,0),colspan=4)
	plt.plot(t,x[:,0],)
	plt.grid(True)
	plt.ylabel("h [km]")
	plt.subplot2grid((6,4),(1,0),colspan=4)
	plt.plot(t,x[:,1],'g')
	plt.grid(True)
	plt.ylabel("V [km/s]")
	plt.subplot2grid((6,4),(2,0),colspan=4)
	plt.plot(t,x[:,2]*180.0/pi,'r')
	plt.grid(True)
	plt.ylabel("gamma [deg]")
	plt.subplot2grid((6,4),(3,0),colspan=4)
	plt.plot(t,x[:,3],'m')
	plt.grid(True)
	plt.ylabel("m [kg]")
	#plt.subplot2grid((6,4),(4,0),colspan=4)
	#plt.plot(t,u[:,0],'k')
	#plt.grid(True)
	#plt.ylabel("alfa [rad]")
	#plt.subplot2grid((6,4),(5,0),colspan=4)
	#plt.plot(t,u[:,1],'c')
	#plt.grid(True)
	#plt.xlabel("t")
	#plt.ylabel("beta [adim]")
	plt.subplots_adjust(0.0125,0.0,0.9,2.5,0.2,0.2)
	plt.show()

	plotRockTraj(t,x,R,tb1,tf-tb2)

	# colocar aqui módulo de calculo de órbita
	h,v,gama,M = x[Nt-1,:]
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


	return None

def plotRockTraj(t,x,R,tb,tb2):

	pi = numpy.pi
	cos = numpy.cos
	sin = numpy.sin

	N = len(t)
	print("N =",N)
	dt = t[1]-t[0]
	X = numpy.empty(numpy.shape(t))
	Z = numpy.empty(numpy.shape(t))

	sigma = 0.0
	X[0] = 0.0
	Z[0] = 0.0
	for i in range(1,N):
		v = x[i,1]
		gama = x[i,2]
		dsigma = v * cos(gama) / (R+x[i,0])
		sigma += dsigma*dt

		X[i] = X[i-1] + dt * v * cos(gama-sigma)
		Z[i] = Z[i-1] + dt * v * sin(gama-sigma)



	print("sigma =",sigma)
	# get burnout point
	itb = int(tb/dt) - 1
	itb2 = int(tb2/dt) - 1
	h,v,gama,M = x[itb,:]
	print("itb =",itb)
	print("State @burnout time:")
	print("h = {:.4E}".format(h)+", v = {:.4E}".format(v)+\
	", gama = {:.4E}".format(gama)+", m = {:.4E}".format(M))


	plt.plot(X,Z)
	plt.grid(True)
	plt.hold(True)
	# Draw burnout point
	#plt.plot(X[:itb],Z[:itb],'r')
	#plt.plot(X[itb],Z[itb],'or')

#	plt.plot([0.0,0.0],[-1.0,0.0],'k')
#	plt.plot([0.0,sin(sigma)],[-1.0,-1.0+cos(sigma)],'k')
	s = numpy.arange(0,1.01,.01)*sigma
	x = R * cos(.5*pi - s)
	z = R * (sin(.5*pi - s) - 1.0)
	#z = -1 + numpy.sqrt(1-x**2)
	plt.plot(x,z,'k')
	plt.plot(X[:itb],Z[:itb],'r')
	plt.plot(X[itb],Z[itb],'or')
	plt.plot(X[itb2:],Z[itb2:],'g')
	plt.plot(X[itb2],Z[itb2],'og')
	plt.plot(X[1]-1,Z[1],'ok')
	plt.xlabel("X [km]")
	plt.ylabel("Z [km]")

	plt.axis('equal')
	plt.title("Rocket trajectory on Earth")
	plt.show()

	return None


def mdlDer(x,t,tVec,alfaProg,betaProg,T,Isp,g0,R):
	h,v,gama,M = x[0],x[1],x[2],x[3]
	betat = interpV(t,tVec,betaProg)
	alfat = interpV(t,tVec,alfaProg)

	btm = betat*T/M
	sinGama = numpy.sin(gama)
	g = g0*(R/(R+h))**2

	return numpy.array([v*sinGama,\
	btm*numpy.cos(alfat) - g*sinGama,\
	btm*numpy.sin(alfat)/v + (v/(h+R)-g/v)*numpy.cos(gama),\
	-btm*M/g0/Isp])

main()



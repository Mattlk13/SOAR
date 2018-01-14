#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 15:35:04 2017

@author: carlos
"""

import numpy


class optimalStagingHeterogeneous():

    def __init__(self, elist: list, Isplist: list, TList: list, vTot: float,
                 Mu: float, g0: float, tol: float):

        self.Mu = Mu
        self.tol = tol
        self.e = numpy.array(elist)
        self.c = numpy.array(Isplist)*g0
        self.T = numpy.array(TList)
        self.vTot = vTot
        self.cMin = numpy.min(self.c)
        self.exp = numpy.exp(1.0)
        self.mflux = self.T/self.c
        self.x = []
        self.v = []
        self.lamb = []
        self.mtot = []
        self.mp = []
        self.me = []
        self.tb = []
        self.tf = []
        self.count = 0

    def functionToBe0(self, x: float) -> float:

        d0 = (1.0 - x/self.c)/self.e
        d1 = d0 ** (self.c/self.vTot)
        error = numpy.prod(d1) - self.exp

        return error

    def bisec(self) -> None:

        count = 0
        x1 = self.cMin/2
        #  print(x1)
        stop = False
        error1 = self.functionToBe0(x1)
        x2 = x1*(1 - self.tol)
        #  print(x2)
        error2 = self.functionToBe0(x2)
        while not stop:

            step = error2*(x2 - x1)/(error2 - error1)

            x1 = x2.copy()
            error1 = error2.copy()

            x2 = x2 - step
            error2 = self.functionToBe0(x2)

            count += 1

            if (abs(error2) < self.tol) or (count == 100):
                stop = True

            if (x2 < 0) or (x2 > self.cMin):
                raise Exception('staging: lagrange multplier out of interval')

        self.x = x2
        self.count = count
        #  print(count)
        return None

    def result(self) -> None:

        self.v = self.c*numpy.log((1 - self.x/self.c)/self.e)
        self.lamb = (numpy.exp(-self.v/self.c) - self.e)/(1 - self.e)

        self.mtot = self.lamb.copy()
        self.me = self.mtot.copy()
        N = len(self.lamb)

        for ii in range(1, N + 1):
            if ii == 1:
                self.mtot[N - ii] = self.Mu/self.lamb[N - ii]
                self.me[N - ii] = self.e[N - ii]*(self.mtot[N - ii] - self.Mu)

            else:
                #  print(N-ii)
                self.mtot[N - ii] = self.mtot[N - ii + 1]/self.lamb[N - ii]
                self.me[N - ii] = self.e[N - ii]*(self.mtot[N - ii] -
                                                  self.mtot[N - ii + 1])

        self.mp = (1 - self.e)*self.me/self.e
        self.tb = self.mp/self.mflux
        self.tf = self.tb.copy()

        for ii in range(1, N):
            self.tf[ii] = self.tf[ii - 1] + self.tb[ii]

        return None

    def show(self) -> None:

        print('inputs:')
        print('e', self.e)
        print('c', self.c)
        print('T', self.T)

        print('\nresults:')
        print('tol', self.tol)
        print('error', self.functionToBe0(self.x))
        print('count', self.count)
        print('vTot', self.vTot)
        print('v', sum(self.v))
        print('mflux', self.mflux)
        print('lamb', self.lamb)
        print('mtot', self.mtot)
        print('mp', self.mp)
        print('me', self.me)
        print('tb', self.tb)
        print('tf', self.tf)

        return None

if __name__ == "__main__":

    con = dict()

    eList = [0.01]#, 0.09, 0.07]
    cList = [350]#, 300, 280]
    TList = [500]#, 500, 60]
    vTot = 1.5*7.0
    tol = 1e-9

    stg = optimalStagingHeterogeneous(eList, cList, TList, vTot, 100, 10e-3,
                                      tol)

    stg.bisec()
    stg.result()
    stg.show()
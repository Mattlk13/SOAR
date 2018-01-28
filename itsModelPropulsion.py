#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 19 16:20:20 2018

@author: carlos
"""

import numpy


class modelPropulsion():

    def __init__(self, p1: object, p2: object, tf: float,
                 v1: float, v2: float, softness: float, Isp: float, T: float):

        # improvements for heterogeneous rocket
        self.Isp = Isp
        self.T = T

        self.t1 = p1.tf[-1]
        t2 = tf - p2.tb[-1]
        self.t3 = tf

        self.v1 = v1
        self.v2 = v2

        f = softness/2

        d1 = self.t1  # width of retangular and 0.5 soft part
        self.c1 = d1*f  # width of the 0.5 soft part
        self.fr1 = d1 - self.c1  # final of the retangular part
        self.fs1 = d1 + self.c1  # final of the retangular part

        d2 = self.t3 - t2  # width of retangular and 0.5 soft part
        self.c2 = d2*f  # width of the 0.5 soft part
        self.r2 = d2 - self.c2  # width of the retangular part
        self.ir2 = t2 + self.c2  # start of the retangular part
        self.is2 = t2 - self.c2  # start of the soft part

        self.dv21 = v2 - v1

        # List of time events and jetsoned masses
        self.tflist = p1.tf[0:-1].tolist() + [self.fr1, self.fs1] + \
            [self.is2, self.ir2, tf]
        self.melist = p1.me[0:-1].tolist() + [0.0, p1.me[-1]] + \
            [0.0, 0.0, p2.me[-1]]

        self.fail = False
        if len(p1.tf) > 2:
            if p1.tf[-2] >= self.fr1:
                self.fail = True

        self.tlist1 = p1.tf[0:-1].tolist()+[self.fs1]
        self.Tlist1 = p1.Tlist
        self.Tlist2 = p2.Tlist

        self.Isp1 = p1.Isp
        self.Isp2 = p2.Isp

    def single(self, t: float)-> float:
        if (t <= self.fr1):
            ans = self.v1
        elif (t <= self.fs1):
            cos = numpy.cos(numpy.pi*(t - self.fr1)/(2*self.c1))
            ans = self.dv21*(1 - cos)/2 + self.v1
        elif (t <= self.is2):
            ans = self.v2
        elif (t <= self.ir2):
            cos = numpy.cos(numpy.pi*(t - self.is2)/(2*self.c2))
            ans = -self.dv21*(1 - cos)/2 + self.v2
        elif (t <= self.t3):
            ans = self.v1
        else:
            ans = 0.0

        return ans

    def value(self, t: float)-> float:
        if (t <= self.fr1):
            ans = self.v1
        elif (t <= self.fs1):
            cos = numpy.cos(numpy.pi*(t - self.fr1)/(2*self.c1))
            ans = self.dv21*(1 - cos)/2 + self.v1
        elif (t <= self.is2):
            ans = self.v2
        elif (t <= self.ir2):
            cos = numpy.cos(numpy.pi*(t - self.is2)/(2*self.c2))
            ans = -self.dv21*(1 - cos)/2 + self.v2
        elif (t <= self.t3):
            ans = self.v1
        else:
            ans = 0.0

        return ans

    def mdlDer(self, t: float)-> tuple:

        return self.value(t), self.Isp, self.T

    def multValue(self, t: float):
        N = len(t)
        ans = numpy.full((N, 1), 0.0)
        for jj in range(0, N):
            ans[jj] = self.value(t[jj])

        return ans


class modelPropulsionHetSimple():

    def __init__(self, p1: object, p2: object, tf: float,
                 v1: float, v2: float):

        # Improvements for heterogeneous rocket
        self.fail = False
        # Total list of specific impulse
        self.Isplist = p1.Isplist + [1.0] + p2.Isplist
        # Total list of Thrust
        self.Tlist = p1.Tlist + [0.0] + p2.Tlist
        # Total list of final t
        t2 = tf - p2.tb[-1]
        self.tflist = p1.tf + [t2, tf]
        # Total list of jettsoned masses
        self.melist = p1.me + [0.0, p2.me[-1]]
        # Total list of Thrust control
        self.vlist = []
        for T in self.Tlist:
            if T > 0.0:
                self.vlist.append(v1)
            else:
                self.vlist.append(v2)

    def getIndex(self, t: float)-> int:
        ii = 0

        while t < self.tf[ii]:
            ii += 1

        return ii

    def single(self, t: float)-> float:
        ii = self.getIndex(t)
        return self.vlist[ii]

    def value(self, t: float)-> float:
        ii = self.getIndex(t)
        return self.vlist[ii]

    def mdlDer(self, t: float)-> tuple:
        ii = self.getIndex(t)
        return self.vlist[ii], self.Isplist[ii], self.Tlist[ii]

    def multValue(self, t: float):
        N = len(t)
        ans = numpy.full((N, 1), 0.0)
        for jj in range(0, N):
            ans[jj] = self.value(t[jj])
        return ans

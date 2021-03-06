import numpy as np
import pylab as pl

######################################################
## - usage from command line:                        #
##     python shallowWater.py --n=1000 --TMAX=0.05   #
##     (where:                                       #
##     n = number of grid cells                      #
##     TMAX = end time simulation)                   #
## - usage from within ipython:                      #
##     from shallowWater import *                    #
##     shallowWater(100,1.,0.01)                     #
######################################################

# Courant Friedrichs Levy condition (CFL) is a necessary condition for convergence
CFL = 0.99 #???# set so it fulfilles CFL condition, experiment with it
# gravitational constant
g = 9.80665

## shallow water solver 1 dimension
def shallowWater(n,XMAX,TMAX):
	TMAX *= XMAX
	
	# dx = cell size
	dx = 1.*XMAX/n
	# x = cell center
	# Make a numpy array starting with a half cell size, ending at XMAX and spacing of
	# cell size which will be a list of cell centers
	x = np.arange(dx/2, XMAX, dx) #set to be cell centers
	
	# initialize height h and momentum hu
	h, hu = initialize(x,XMAX)

	# add ghost cells
	h = addGhostCells(h)
	hu = addGhostCells(hu)
	# plot initial conditions with interactive mode on
	pl.ion()
	plotVars(x,h,hu,0)
	
	# time starts at zero
	tsum=0.
	saveToFile(h,tsum,n,'result.dat','w')
	saveToFile(hu,tsum,n,'result.dat','a')
	# loop over time
	while tsum<TMAX:
		# apply boundary conditions
		h = neumannBoundaryConditions(h)
		hu = neumannBoundaryConditions(hu)
		#h = periodicBoundaryConditions(h)
		#hu = periodicBoundaryConditions(hu)

		# calculate fluxes at cell interfaces and largest eigenvalue
		fhp, fhup, eigp = fluxes(h[1:],hu[1:])
		fhm, fhum, eigm = fluxes(h[:-1],hu[:-1])
		maxeig = max(eigp, eigm) #???# maximum of eigp and eigm

		# calculate time step according to CFL-condition
		dt = calculateDt(dx,maxeig,tsum,TMAX)
		# advance time
		tsum = tsum+dt
		lambd = 1.*dt/dx

		# R = Lax-Friedrichs Flux
		Rh = LxFflux(h,fhp, fhm, lambd)
		Rhu = LxFflux(hu, fhup, fhum, lambd)

		h[1:-1] -= lambd*(Rh[1:]-Rh[:-1])  #???# update cell average (tip: depends on Rh and lambda)
		hu[1:-1] -= lambd*(Rhu[1:]-Rhu[:-1]) #???# update cell average (tip: depends on Rhu and lambda)
	
	       # DEBUG
                #print np.sum(h)
                
                plotVars(x,h,hu,tsum)

	#end while (time loop)
	saveToFile(h,tsum,n,'result.dat','a')
	saveToFile(hu,tsum,n,'result.dat','a')
	error('result.dat', 'result_n1000_TMAX045.dat') # Check the error
	
def plotVars(x,h,hu,time,clear=True):
	time = '{0:.5f}'.format(time)
	pl.figure(1)
	if clear:
		pl.clf()
	pl.subplot(211)
	pl.title('water height h(t='+time+')')
	pl.plot(x,h[1:-1],label='u') #h[1:-1] = results in a list with all elements except the elements at index 0 and the last index
	pl.xlabel('x')
	pl.legend()
	pl.subplot(212)
	pl.title('momentum hu(t='+time+')')
	pl.plot(x,hu[1:-1],label='hu')
	pl.xlabel('x')
	pl.legend()
	pl.draw()
	
def saveToFile(v,t,n,name,mode):
	# mode 'w' (over)writes, 'a' appends
    v = np.hstack([t,CFL,g,n+2,v]) # +2 because of ghost cells
    ff = open(name, mode+'b')
    v.tofile(ff)
    ff.close()
    
def readFromFile(name,clear=True):
    ff = open(name, 'rb')
    data = np.fromfile(ff)
    ff.close()
    numberCells = data[3]
    n = numberCells-2 # -2 because of ghost cells
    numberParameters = 4 # t, CFL, g, n
    numberVariables = 2 # h,hu
    if data.size%(numberCells+numberParameters)*numberVariables==0:
        numberSavedTimeSteps = data.size/((numberCells+numberParameters)*numberVariables)
        data.shape = (numberVariables*numberSavedTimeSteps,(numberCells+numberParameters))
        # plot the last time step
        pl.ion()
        plotVars((1./2. + np.arange(n))/n, data[-2,numberParameters:], data[-1,numberParameters:], data[-1,0], clear)
    else:
        print 'data file inconsistent'
    return data

def error(name,nameReference):
	data = readFromFile(name,True)
	dataRef = readFromFile(nameReference,False)
	numberParameters = 4 # t, CFL, g, n
	h = data[-2,numberParameters+1:-1]
	hu = data[-1,numberParameters+1:-1]
	h_ref = dataRef[-2,numberParameters+1:-1]
	hu_ref = dataRef[-1,numberParameters+1:-1]
	
	
	numberCells = data[0,3]
	if (numberCells != dataRef[0,3]):
		print 'solution and reference solution have different number of grid cells'
	else: 
		n = numberCells-2 # -2 because of ghost cells
		time = data[-1,0]
		timeRef = dataRef[-1,0]
		if time==timeRef: 
			relErrorh = np.sum(np.abs(h-h_ref))/np.sum(np.abs(h_ref))
			absErrorhu = np.sum(np.abs(h-h_ref))/(1.*n)
			time = '{0:.5f}'.format(time)
			relErrorh = '{0:.5f}'.format(relErrorh*100.)
			absErrorhu = '{0:.5f}'.format(absErrorhu*100.)
			print 'relative L1-error of water height h(t='+time+') is '+relErrorh+'%'
			print 'absolute L1-error of momentum hu(t='+time+') is '+absErrorhu+'%'
		else:
			print 'cannot compare solution at different times'	
			
def initialize(x,XMAX):
	# initialize water height with two peaks
	c = 0.01
	h = .5 + .5*np.exp(-(2.*(x/XMAX-.6))**2/(2.*c**2))
	h += np.exp(-(2.*(x/XMAX-.4))**2/(2.*c**2))
	# momentum is zero
	hu = 0.*x
	return h, hu

def addGhostCells(var):	
	return np.hstack([0.,var,0.])

def neumannBoundaryConditions(var):
	var[0] = var[1]
	var[-1] = var[-2]
	return var #???# var with neumann boundary conditions

def periodicBoundaryConditions(var):
	var[0] = var[-2]
	var[-1] = var[1] 
	return var #???# var with periodic boundary conditions

def calculateDt(dx,maxeig,tsum,TMAX):
	dt = CFL*dx/maxeig # Update according to CFL condition
	
	# Just resets time if it goes above max time
	if tsum + dt > TMAX:
		dt = TMAX - tsum
	
	return dt #???# stepsize dtdt

def fluxes(h,hu):
	fh,fhu,lambd1,lambd2 = fluxAndLambda(h,hu)
	
	# Finding the maximum value of each element in lambd1 and lambd2, finding the maximum
	# value in that result
	# maxeig = np.amax(np.maximum(lambd1, lambd2)) #???# calculate largest eigenvalue
	maxeig = np.max(np.maximum(np.abs(lambd1),np.abs(lambd2)))
	return fh, fhu, maxeig

def LxFflux(q, fqm, fqp, lambd):
	R = 0.5*( (fqp+fqm) - 1./lambd*(q[1:] - q[:-1]) )
	return R #???# Lax-Friedrichs Flux

def fluxAndLambda(h,hu):
	c = np.sqrt(g*h)
	h = np.maximum(0.5,h)
	u = hu/h
	
	fh = hu
	fhu = hu*u+.5*g*h*h
	lambda1 = u + c
	lambda2 = u - c
	
	return fh, fhu, lambda1, lambda2 #???# fluxes fh and fhu and eigenvalues lambda1, lambda2

if __name__ == "__main__":

	from optparse import OptionParser
	usage = "usage: %prog [var=value]"
	p = OptionParser(usage)
	p.add_option("--n", type="int", help="number of points")
	p.add_option("--XMAX", type="float", help="length of domain")
	p.add_option("--TMAX", type="float", help="time of simulation")
	(opts, args) = p.parse_args()
	if opts.n == None:
		n = 1000 #100
	else:
		n = opts.n
	if opts.XMAX == None:
		XMAX = 1.0
	else:
		XMAX = opts.XMAX
	if opts.TMAX == None:
		TMAX = .045 #.02
	else:
		TMAX = opts.TMAX

	shallowWater(n,XMAX,TMAX)


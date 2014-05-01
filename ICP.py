"""
ICP.py
iterative closest point fitting of 2 point clouds using rigid + scaling
transforms

Ju Zhang
29-June-2012
"""
import scipy
from scipy.spatial import cKDTree
from scipy.optimize import leastsq
#import numpy as N
import numpy as np

#======================================================================#
def transformRigid3D( x, t ):
    """ applies a rigid transform to list of points x.
    t = (tx,ty,tz,rx,ry,rz)
    """
    X = scipy.vstack( (x.T, scipy.ones(x.shape[0]) ) )
    T = scipy.array([[1.0, 0.0, 0.0, t[0]],\
               [0.0, 1.0, 0.0, t[1]],\
               [0.0, 0.0, 1.0, t[2]],\
               [1.0, 1.0, 1.0, 1.0]])
        
    Rx = scipy.array( [[1.0, 0.0, 0.0],\
                 [0.0, scipy.cos(t[3]), -scipy.sin(t[3])],\
                 [0.0, scipy.sin(t[3]),  scipy.cos(t[3])]] )
    
    Ry = scipy.array( [[scipy.cos(t[4]), 0.0, scipy.sin(t[4])],\
                 [0.0, 1.0, 0.0],\
                 [-scipy.sin(t[4]), 0.0, scipy.cos(t[4])]] )
    
    Rz = scipy.array( [[scipy.cos(t[5]), -scipy.sin(t[5]), 0.0],\
                 [scipy.sin(t[5]), scipy.cos(t[5]), 0.0],\
                 [0.0, 0.0, 1.0]] )
    
    T[:3,:3] = scipy.dot( scipy.dot( Rx,Ry ),Rz )
    return scipy.dot( T, X )[:3,:].T

def translateRigid3D( x, t ):
    """ applies a rigid transform to list of points x.
    T = (tx,ty,tz,rx,ry,rz)
    """
    X = scipy.vstack( (x.T, scipy.ones(x.shape[0]) ) )
    T = scipy.array([[1.0, 0.0, 0.0, t[0]],\
               [0.0, 1.0, 0.0, t[1]],\
               [0.0, 0.0, 1.0, t[2]],\
               [1.0, 1.0, 1.0, 1.0]])
        
#    Rx = scipy.array( [[1.0, 0.0, 0.0],\
#                 [0.0, scipy.cos(t[3]), -scipy.sin(t[3])],\
#                 [0.0, scipy.sin(t[3]),  scipy.cos(t[3])]] )
#    
#    Ry = scipy.array( [[scipy.cos(t[4]), 0.0, scipy.sin(t[4])],\
#                 [0.0, 1.0, 0.0],\
#                 [-scipy.sin(t[4]), 0.0, scipy.cos(t[4])]] )
#    
#    Rz = scipy.array( [[scipy.cos(t[5]), -scipy.sin(t[5]), 0.0],\
#                 [scipy.sin(t[5]), scipy.cos(t[5]), 0.0],\
#                 [0.0, 0.0, 1.0]] )
    
#    T[:3,:3] = scipy.dot( scipy.dot( Rx,Ry ),Rz )
    return scipy.dot( T, X )[:3,:].T

def rotateRigid3D( x, t ):
    """ applies a rigid rotation to list of points x.
    t = (tx,ty,tz,rx,ry,rz)
    """
    X = scipy.vstack( (x.T, scipy.ones(x.shape[0]) ) )
    T = scipy.array([[1.0, 0.0, 0.0, 0.0],\
               [0.0, 1.0, 0.0, 0.0],\
               [0.0, 0.0, 1.0, 0.0],\
               [1.0, 1.0, 1.0, 1.0]])
        
    Rx = scipy.array( [[1.0, 0.0, 0.0],\
                 [0.0, scipy.cos(t[3]), -scipy.sin(t[3])],\
                 [0.0, scipy.sin(t[3]),  scipy.cos(t[3])]] )
    
    Ry = scipy.array( [[scipy.cos(t[4]), 0.0, scipy.sin(t[4])],\
                 [0.0, 1.0, 0.0],\
                 [-scipy.sin(t[4]), 0.0, scipy.cos(t[4])]] )
    
    Rz = scipy.array( [[scipy.cos(t[5]), -scipy.sin(t[5]), 0.0],\
                 [scipy.sin(t[5]), scipy.cos(t[5]), 0.0],\
                 [0.0, 0.0, 1.0]] )
    
    T[:3,:3] = scipy.dot( scipy.dot( Rx,Ry ),Rz )
    return scipy.dot( T, X )[:3,:].T


def transformScale3D( x, S ):
    """ applies scaling to a list of points x. S = (sx,sy,sz)
    """
    return scipy.multiply( x, S )

def matchCentroid(x, S):
    """translate centroid of points S to centroid of points x"""
    # calculate centroids of each point set
    cx = np.mean(x, axis=0)
    cS = np.mean(S, axis=0)
    
    # difference 
    delta = cx - cS

    # add a column of 1s to the points to be transformed    
    S = scipy.vstack( (S.T, scipy.ones(S.shape[0]) ) )
 
    T = scipy.array([[1.0, 0.0, 0.0, delta[0]],\
               [0.0, 1.0, 0.0, delta[1]],\
               [0.0, 0.0, 1.0, delta[2]],\
               [1.0, 1.0, 1.0, 1.0]])
    
    return delta, scipy.dot( T, S )[:3,:].T

def boundingBox(x):
    """Compute the bounding box of points x"""
    min_ = np.min(x, axis=0)
    max_ = np.max(x, axis=0)
    return min_, max_

#======================================================================#
def fitDataEPDP( X, data, xtol=1e-5, maxfev=0, translate=True, rotate=True, scale=True):
    """ fit list of points X to list of points data by minimising
    least squares distance between each point in X and closest neighbour
    in data. Rigid transformation plus scaling.
    
    return:
    tOpt: optimised transformations [tx, ty, tz, rx, ry, rz, s]
    XOpt: transformed points
    """

    dataTree = cKDTree( data )
    X = scipy.array(X)
    
    def obj( t ):
        # FIXME: there should be a way to compose this as a sequence of
        # numpy arrays, which would probably be more efficient
        # See Mithraratne 2006 Customisation of anatomically based musculoskeletal structures
        
        if translate and not rotate:
            xR = translateRigid3D( X, t[:6] )
        elif not translate and rotate:
            xR = rotateRigid3D( X, t[:6] )
        elif translate and rotate:
            xR = transformRigid3D( X, t[:6] )
        elif not translate and not rotate:
            xR = X
            
        if scale:
            xRS = transformScale3D( xR, scipy.ones(3)*t[6] )
        else:
            xRS = xR

        d = dataTree.query( list(xRS) )[0]
        #~ print d.mean()
        return d*d        
    
    t0 = scipy.array([0.0,0.0,0.0,0.0,0.0,0.0,1.0])
    tOpt = leastsq( obj, t0, xtol=xtol, maxfev=maxfev )[0]
    
    if translate and not rotate:
        XOpt = translateRigid3D( X, tOpt[:6] )
    elif not translate and rotate:
        XOpt = rotateRigid3D( X, tOpt[:6] )
    elif translate and rotate:
        XOpt = transformRigid3D( X, tOpt[:6] )
    elif not translate and not rotate:
        XOpt = X

    if scale:
        XOpt = transformScale3D( XOpt, tOpt[6:] )
    
    return tOpt, XOpt

def fitDataEPDP2( X, data, xtol=1e-5, maxfev=0, translate=True, rotate=True, scale=True):
    """ fit list of points X to list of points data by minimising
    least squares distance between each point in X and closest neighbour
    in data. Rigid transformation plus scaling in three directions.
    
    return:
    tOpt: optimised transformations [tx, ty, tz, rx, ry, rz, sx, sy, sz]
    XOpt: transformed points
    
    FIXME: this is not working yet
    """

    dataTree = cKDTree( data )
    X = scipy.array(X)
    
    def transform(X, t):
        # Rotation matrix
        Rx = scipy.array( [[1.0, 0.0, 0.0],\
                     [0.0, scipy.cos(t[3]), -scipy.sin(t[3])],\
                     [0.0, scipy.sin(t[3]),  scipy.cos(t[3])]] )
        
        Ry = scipy.array( [[scipy.cos(t[4]), 0.0, scipy.sin(t[4])],\
                     [0.0, 1.0, 0.0],\
                     [-scipy.sin(t[4]), 0.0, scipy.cos(t[4])]] )
        
        Rz = scipy.array( [[scipy.cos(t[5]), -scipy.sin(t[5]), 0.0],\
                     [scipy.sin(t[5]), scipy.cos(t[5]), 0.0],\
                     [0.0, 0.0, 1.0]] )
    
        R = scipy.dot( scipy.dot( Rx,Ry ),Rz )
        
        # Scaling matrix
        s = scipy.array(
                        [[t[6], 0.0, 0.0],\
                         [0.0, t[7], 0.0],\
                         [0.0, 0.0, t[8]]])
        
        # Translation matrix
        dX = scipy.array([t[0], t[1], t[2]])
        
        xR = ((s.dot(R)).dot(X.T)).T - dX
        print X[0]
        print ((s.dot(R)).dot(X.T)).T[0]
        print xR[0]
        
        return xR
    
    def obj( t ):
        # FIXME: there should be a way to compose this as a sequence of
        # numpy arrays, which would probably be more efficient
        # See Mithraratne 2006 Customisation of anatomically based musculoskeletal structures
        
        xR = transform(X, t)
        
        d = dataTree.query( list(xR) )[0]
        #~ print d.mean()
        return d*d        
    
    t0 = scipy.array([0.0,0.0,0.0,0.0,0.0,0.0,1.0,1.0,1.0])
    tOpt = leastsq( obj, t0, xtol=xtol, maxfev=maxfev )[0]
    
    XOpt = transform(X, tOpt)
        
    return tOpt, XOpt


#======================================================================#
def fitDataRigidScaleEPDP( X, data, xtol=1e-5, maxfev=0):
    """ fit list of points X to list of points data by minimising
    least squares distance between each point in X and closest neighbour
    in data. Rigid transformation plus scaling.
    
    return:
    tOpt: optimised transformations [tx, ty, tz, rx, ry, rz, s]
    XOpt: transformed points
    """
    scale = False
    dataTree = cKDTree( data )
    X = scipy.array(X)
    
    def obj( t ):
        xR = transformRigid3D( X, t[:6] )
        if scale:
            xRS = transformScale3D( xR, scipy.ones(3)*t[6] )
        else:
            xRS = xR
        d = dataTree.query( list(xRS) )[0]
        #print d.mean()
        return d*d
    
    t0 = scipy.array([0.0,0.0,0.0,0.0,0.0,0.0,1.0])
    tOpt = leastsq( obj, t0, xtol=xtol, maxfev=maxfev )[0]
    XOpt = transformRigid3D( X, tOpt[:6] )
    if scale:
        XOpt = transformScale3D( XOpt, tOpt[6:] )
    
    return tOpt, XOpt

def fitDataRigidEPDP( X, data, xtol=1e-5, maxfev=0 ):
    """ fit list of points X to list of points data by minimising
    least squares distance between each point in X and closest neighbour
    in data. Rigid transformation only.
    
    return:
    tOpt: optimised transformations [tx, ty, tz, rx, ry, rz, s]
    XOpt: transformed points
    """
    
    dataTree = cKDTree( data )
    X = scipy.array(X)
    
    def obj( t ):
        xR = transformRigid3D( X, t[:6] )
        #xR = translateRigid3D( X, t[:6] )
        #xRS = transformScale3D( xR, scipy.ones(3)*t[6] )
        #d = dataTree.query( list(xRS) )[0]
        d = dataTree.query( list(xR) )[0]
        #~ print d.mean()
        return d*d
    
    t0 = scipy.array([0.0,0.0,0.0,0.0,0.0,0.0,1.0])
    tOpt = leastsq( obj, t0, xtol=xtol, maxfev=maxfev )[0]
    XOpt = transformRigid3D( X, tOpt[:6] )
    #XOpt = transformScale3D( XOpt, tOpt[6:] )
    
    return tOpt, XOpt

    
def fitDataRigidScaleDPEP( X, data, xtol=1e-5, maxfev=0 ):
    """ fit list of points x to list of points data by minimising
    least squares distance between each point in data and closest
    neighbour in X.  Rigid transformation plus scaling.
    
    return:
    tOpt: optimised transformations [tx, ty, tz, rx, ry, rz, s]
    XOpt: transformed points
    """
    X = scipy.array(X)

    def obj( t ):
        xR = transformRigid3D( X, t[:6] )
        xRS = transformScale3D( xR, scipy.ones(3)*t[6] )
        xTree = cKDTree( xRS )
        d = xTree.query( list(data) )[0]
        #~ print d.mean()
        return d*d
    
    t0 = scipy.array([0.0,0.0,0.0,0.0,0.0,0.0,1.0])
    tOpt = leastsq( obj, t0, xtol=xtol, maxfev=maxfev )[0]
    XOpt = transformRigid3D( X, tOpt[:6] )
    XOpt = transformScale3D( XOpt, tOpt[6:] )
    
    return tOpt, XOpt

def transformToMatrix( t ):
    """ converts a rigid transform to a transformation matrix
    t = (tx,ty,tz,rx,ry,rz)
    """
    T = scipy.array([[1.0, 0.0, 0.0, t[0]],\
               [0.0, 1.0, 0.0, t[1]],\
               [0.0, 0.0, 1.0, t[2]],\
               [1.0, 1.0, 1.0, 1.0]])

    Rx = scipy.array( [[1.0, 0.0, 0.0],\
                 [0.0, scipy.cos(t[3]), -scipy.sin(t[3])],\
                 [0.0, scipy.sin(t[3]),  scipy.cos(t[3])]] )

    Ry = scipy.array( [[scipy.cos(t[4]), 0.0, scipy.sin(t[4])],\
                 [0.0, 1.0, 0.0],\
                 [-scipy.sin(t[4]), 0.0, scipy.cos(t[4])]] )

    Rz = scipy.array( [[scipy.cos(t[5]), -scipy.sin(t[5]), 0.0],\
                 [scipy.sin(t[5]), scipy.cos(t[5]), 0.0],\
                 [0.0, 0.0, 1.0]] )

    T[:3,:3] = scipy.dot( scipy.dot( Rx,Ry ),Rz )
    return T

def affineTransform(Xo, Xt):
    """Computes the affine transformation (translation, rotation, shearing, scaling)
    that best matches the target points Xt to the landmark points Xo.
    Author: Glenn Ramsey, translated from Kumar Mithrarathne's matlab script direct2.m """

    N = len(Xo)
    # at least 4 points are needed
    assert(N>=4)
    # both sets of points must be the same length
    assert(N==len(Xt))

    A1 = np.transpose(Xo).dot(Xo)

    # make A1 4x4 and put sum(Xo) in the extra places, except
    # for A1(4,4) which contains the number of points

    x = np.array(Xo).sum(axis=0)
    A1 = np.vstack((A1, x))
    n = np.array([N])
    x = np.hstack(([x], [n]))
    #x[3,0] = N
    A1 = np.hstack((A1, x.T))

    #B1 = Xo'*Xt;
    #B1(4,:) = sum(Xt);

    #Taffine1 = [(inv(A1)*B1)';0 0 0 1]

    x = np.array(Xt).sum(axis=0)
    B1 = np.transpose(Xo).dot(Xt)
    B1 = np.vstack((B1, x))

    T1 = np.transpose(np.linalg.inv(A1).dot(B1))
    x = np.array([[0,0,0,1]])
    T1 = np.vstack((T1, x))
    return T1

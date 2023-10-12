import cv2 as cv
import numpy as np
import pyzbar.pyzbar as pyzbar
import config as cfg


# A function to search an image for QR codes and return the decoded codes
def decode(im):
    decodedQrCodes = pyzbar.decode(im, symbols=[pyzbar.ZBarSymbol.QRCODE])
    if len(decodedQrCodes) > 0:
        print(decodedQrCodes)
    return decodedQrCodes


# A funtion to take an image
def findAnchorPoints(img, visualize, low, high):
    # Finds coords of the anchor objects (screws, stickers, etc) used  to find the transform and base coords off of
    # Makes some assumptions:
    # - there are exactly 4 anchor objects, which lie in 1 plane arranged on the corners of a square in that plane
    # - the anchor objects are a different color from the rest of the image
    points = []

    imageHSV = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    mask = cv.inRange(imageHSV, low, high)
    contours, _ = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

    if visualize:
        imageMask = cv.bitwise_and(img, img, mask=mask)
        cv.imshow('Mask', imageMask)

    if len(contours) != 4:  # May need to add a loop where we attempt to fix the contour number
        print(f'Wrong number of anchor point contours! ({len(contours)} contours, should be 4). Attempting to fix...')
        contours[:] = [c for c in contours if not cv.moments(c)["m00"] < 100*cfg.K_ratio]

        if len(contours) != 4:
            print(f'Wrong number of contours after fix! ({len(contours)} contours, should be 4)')
        else:
            print('Successfully fixed contour number!')

    if len(contours) == 4:
        for c in contours:
            M = cv.moments(c)
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            points.append((cX, cY))

    if points != []:
        return points


# A function to return the coordinates of the center of the laser pointer dot in an image
def findLaserPoint(img, visualize, threshold): 
    imageGray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    ret, imageThresh = cv.threshold(imageGray, threshold, 255, cv.THRESH_TOZERO)
    contours, _ = cv.findContours(imageThresh, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)
    (cX, cY) = (-1, -1)  # Initializing these to unreachable coords

    # Converting back to color so the contours can be drawn on in color afterwards
    imageCont = cv.cvtColor(imageThresh, cv.COLOR_GRAY2BGR)

    if visualize:
        cv.drawContours(imageCont, contours, -1, (0,255,0), 1)
        cv.imshow('Threshold', imageCont)

    # May need to add a loop where we try to fix the contour number

    if len(contours) != 1:
        print(f'Wrong number of laser dot contours! ({len(contours)} contours, should be 1)')

    for c in contours:
        M = cv.moments(c)
        if 0 < M["m00"] < 400*cfg.K_ratio:  # The laser dot contour won't be too big or small
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])

    # Note that if this returns (-1, -1), it has failed to find anything
    return (cX, cY)
        

# This is a modified version of imutils's perspective.order_points() function which avoids a bug
# that was caused by extreme perspective foreshortening
def orderAnchorPoints(pts):

    # sort the points based on their x-coordinates
    xSorted = pts[np.argsort(pts[:, 0]), :]

    # grab the left-most and right-most points from the sorted
    # x-roodinate points
    leftMost = xSorted[:2, :]
    rightMost = xSorted[2:, :]

    # now, sort the left-most coordinates according to their
    # y-coordinates so we can grab the top-left and bottom-left
    # points, respectively
    leftMost = leftMost[np.argsort(leftMost[:, 1]), :]
    (tl, bl) = leftMost

    # This is the modified bit. Sort the right-most coords by y coordinate, just like the left-most coords
    rightMost = rightMost[np.argsort(rightMost[:, 1]), :]
    (tr, br) = rightMost
    # return the coordinates in top-left, top-right,
    # bottom-right, and bottom-left order
    return np.array([tl, tr, br, bl], dtype="float32")
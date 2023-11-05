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


def findAnchorPoints(img, visualize, low, high):
    """Take an image and return the anchor points found within"""
    # Finds coords of the anchor objects (screws, stickers, etc.) used  to find the transform and base coords off of
    # Makes some assumptions:
    # - there are exactly 4 anchor objects, which lie in 1 plane arranged on the corners of a square in that plane
    # - the anchor objects are a different color from the rest of the image
    points = []

    imageHSV = cv.cvtColor(img, cv.COLOR_BGR2HSV)
    mask = cv.inRange(imageHSV, low, high)
    contours, _ = cv.findContours(mask, cv.RETR_TREE, cv.CHAIN_APPROX_SIMPLE)

    contour_list = list(contours)  # contours is a tuple, which we cannot modify

    if visualize:
        print('hello')
        imageMask = cv.bitwise_and(img, img, mask=mask)
        cv.drawContours(imageMask, contour_list, -1, (0, 0, 255), 1)
        cv.imshow('Mask', imageMask)
        print('hi')
        cv.waitKey(15)

    if len(contour_list) != 4:  # May need to add a loop where we attempt to fix the contour number
        print(f'Wrong number of anchor point contours! ({len(contour_list)} contours, should be 4). Attempting to fix...')
        contour_list[:] = [c for c in contour_list if 200*cfg.K_ratio < cv.moments(c)["m00"] < 500*cfg.K_ratio]

        if len(contour_list) != 4:
            print(f'Wrong number of contours after fix! ({len(contour_list)} contours, should be 4)')
        else:
            print('Successfully fixed contour number!')

    if len(contour_list) == 4:
        for c in contour_list:
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
        cv.drawContours(imageCont, contours, -1, (0, 255, 0), 1)
        cv.imshow('Threshold', imageCont)
        cv.waitKey(1)

    # May need to add a loop where we try to fix the contour number

    if len(contours) != 1:
        print(f'Wrong number of laser dot contours! ({len(contours)} contours, should be 1)')

    for c in contours:
        M = cv.moments(c)
        if 0 < M["m00"] < 10*cfg.K_ratio:  # The laser dot contour won't be too big or small
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


def mark_up_image(image, laser_coords, emitter_coords):
    """
    Return a version of the image marked upto visualize various data.
    e.g. marking the positions of the laser dot, emitter slit, adding a mm scale reference, etc.
    """
    if cfg.E_PID_laser_coords_ready.is_set():
        cv.putText(image,
                   f'. Laser Dot ({laser_coords[0]}, {laser_coords[1]})',
                   laser_coords, cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 50), 2)
        cv.putText(image,
                   f'. Emitter Slit ({emitter_coords[0]}, {emitter_coords[1]})',
                   emitter_coords, cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 50), 2)

    scaleSquareCoord = int(10 + 10 * (cfg.K_pixel2mm_constant ** -1))
    cv.rectangle(image, (10, 10), (scaleSquareCoord, scaleSquareCoord), (255, 200, 50), 2)
    cv.putText(image, '10 mm', (scaleSquareCoord + 5, scaleSquareCoord),
               cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 50), 2)

    # a = self.transform.dot((anchor_coords[0][0], anchor_coords[0][1], 1))
    # a /= a[2]
    # cv.putText(self.image, f'{a}', (10,100), cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,200,50), 2)

    # TODO: This above bit works, but because the anchor points never get updated, it will always just
    #  output [350,650,1] for a. And really, the code is not written to ever update the anchor points.
    #  Talk to Jack/maybe other people at the lab meeting to figure out if we can just assume the anchor
    #  points will not be moving

def calc_processing_time(prefix, time, time_list, pop_size):
    """
    Take the amount of time a processing step took, a list of past times to append to, the max length of that list,
    and then print formatted info about how long that step takes on average.
    """

    time_list.append(time)
    if len(time_list) > pop_size:
        time_list.pop(0)
    print(f'a {prefix}: {round(sum(time_list)/len(time_list),5)}')

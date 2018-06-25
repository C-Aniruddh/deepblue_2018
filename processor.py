from pyimagesearch.transform import four_point_transform
from pyimagesearch import imutils
from skimage.filters import threshold_adaptive
import numpy as np
import cv2
import os

class Processor:

    def scan_form(self, form_name, form_image_path):

        # load the image and compute the ratio of the old height
        # to the new height, clone it, and resize it
        image = cv2.imread(form_image_path)
        ratio = image.shape[0] / 500.0
        orig = image.copy()
        image = imutils.resize(image, height=500)
        # convert the image to grayscale, blur it, and find edges
        # in the image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(gray, 75, 200)

        # show the original image and the edge detected image
        print("STEP 1: Edge Detection")
        # cv2.imshow("Image", image)
        # cv2.imshow("Edged", edged)

        # find the contours in the edged image, keeping only the
        # largest ones, and initialize the screen contour
        _, cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]

        print("Found contours")

        # loop over the contours
        for c in cnts:
            # approximate the contour
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            # if our approximated contour has four points, then we
            # can assume that we have found our screen
            if len(approx) == 4:
                screenCnt = approx
                break
        # show the contour (outline) of the piece of paper
        print("STEP 2: Find contours of paper")
        cv2.drawContours(image, [screenCnt], -1, (0, 255, 0), 2)
        # cv2.imshow("Outline", image)

        # apply the four point transform to obtain a top-down
        # view of the original image
        warped = four_point_transform(orig, screenCnt.reshape(4, 2) * ratio)

        # convert the warped image to grayscale, then threshold it
        # to give it that 'black and white' paper effect
        # warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        # warped = threshold_adaptive(warped, 251, offset = 10)
        # warped = warped.astype("uint8") * 255

        # show the original and scanned images
        print("STEP 3: Apply perspective transform")
        # cv2.imshow("Original", orig)
        # cv2.imshow("Scanned", warped)


        print("SAVE")
        # cv2.imwrite("scanned.jpg", imutils.resize(warped, height = 450))
        # cv2.imwrite("scanned.jpg", warped)
        print("CROP")

        img = warped
        height, width, channels = img.shape
        end_h = int(height - 10)
        end_w = int(width - 10)

        crop_img = img[10:end_h, 10:end_w]

        print("SAVE CROP")

        APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
        filename = '%s_scanned.jpg' % form_name
        final_filename = '%s/%s_scanned.jpg' % (UPLOAD_FOLDER, form_name)
        cv2.imwrite(final_filename, crop_img)

        print("Done")

        w = crop_img.shape[0]
        h = crop_img.shape[1]

        return w, h, filename

    def scan_form_later(self, form_name, form_image_path):

        # load the image and compute the ratio of the old height
        # to the new height, clone it, and resize it
        image = cv2.imread(form_image_path)
        ratio = image.shape[0] / 500.0
        orig = image.copy()
        image = imutils.resize(image, height=500)
        # convert the image to grayscale, blur it, and find edges
        # in the image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(gray, 75, 200)

        # show the original image and the edge detected image
        print("STEP 1: Edge Detection")
        # cv2.imshow("Image", image)
        # cv2.imshow("Edged", edged)

        # find the contours in the edged image, keeping only the
        # largest ones, and initialize the screen contour
        _, cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]

        print("Found contours")

        # loop over the contours
        for c in cnts:
            # approximate the contour
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            # if our approximated contour has four points, then we
            # can assume that we have found our screen
            if len(approx) == 4:
                screenCnt = approx
                break
        # show the contour (outline) of the piece of paper
        print("STEP 2: Find contours of paper")
        cv2.drawContours(image, [screenCnt], -1, (0, 255, 0), 2)
        # cv2.imshow("Outline", image)

        # apply the four point transform to obtain a top-down
        # view of the original image
        warped = four_point_transform(orig, screenCnt.reshape(4, 2) * ratio)

        # convert the warped image to grayscale, then threshold it
        # to give it that 'black and white' paper effect
        # warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        # warped = threshold_adaptive(warped, 251, offset = 10)
        # warped = warped.astype("uint8") * 255

        # show the original and scanned images
        print("STEP 3: Apply perspective transform")
        # cv2.imshow("Original", orig)
        # cv2.imshow("Scanned", warped)


        print("SAVE")
        # cv2.imwrite("scanned.jpg", imutils.resize(warped, height = 450))
        # cv2.imwrite("scanned.jpg", warped)
        print("CROP")

        img = warped
        height, width, channels = img.shape
        end_h = int(height - 10)
        end_w = int(width - 10)

        crop_img = img[10:end_h, 10:end_w]

        print("SAVE CROP")

        APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
        filename = '%s_scanned_process.jpg' % form_name
        final_filename = '%s/%s_scanned_process.jpg' % (UPLOAD_FOLDER, form_name)
        cv2.imwrite(final_filename, crop_img)

        print("Done")

        w = crop_img.shape[0]
        h = crop_img.shape[1]

        return w, h, final_filename

    def get_details(self, form_name, image_path):
        image = cv2.imread(image_path)
        w = image.shape[0]
        h = image.shape[1]
        filename = '%s_scanned_process.jpg' % form_name
        APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static/uploads')
        final_filename = '%s/%s_scanned_process.jpg' % (UPLOAD_FOLDER, form_name)
        cv2.imwrite(final_filename, image)
        return w, h, filename
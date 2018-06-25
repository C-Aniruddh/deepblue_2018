from pyimagesearch.transform import four_point_transform
from pyimagesearch import imutils
from skimage.filters import threshold_adaptive
from keras.models import model_from_yaml
from scipy.misc import imsave, imread, imresize
from skimage.feature import hog
import numpy as np
import os
import argparse
import cv2
import pickle

APP_ROOT = os.path.dirname(os.path.abspath(__file__))


class Helpers:

    def __init__(self):
        self.bin_path_text = os.path.join(APP_ROOT, 'bin_text')
        self.bin_path_num = os.path.join(APP_ROOT, 'bin_num')
        self.model_text = self.load_model(self.bin_path_text)
        self.mapping_text = pickle.load(open('%s/mapping.p' % self.bin_path_text, 'rb'))
        self.model_num = self.load_model(self.bin_path_num)
        self.mapping_num = pickle.load(open('%s/mapping.p' % self.bin_path_num, 'rb'))

    def load_model(self, bin_dir):
        ''' Load model from .yaml and the weights from .h5

            Arguments:
                bin_dir: The directory of the bin (normally bin/)

            Returns:
                Loaded model from file
        '''

        # load YAML and create model
        yaml_file = open('%s/model.yaml' % bin_dir, 'r')
        loaded_model_yaml = yaml_file.read()
        yaml_file.close()
        model = model_from_yaml(loaded_model_yaml)

        # load weights into new model
        model.load_weights('%s/model.h5' % bin_dir)
        return model

    def sort_contours(self, cnts, method="left-to-right"):
        # initialize the reverse flag and sort index
        reverse = False
        i = 0

        # handle if we need to sort in reverse
        if method == "right-to-left" or method == "bottom-to-top":
            reverse = True

        # handle if we are sorting against the y-coordinate rather than
        # the x-coordinate of the bounding box
        if method == "top-to-bottom" or method == "bottom-to-top":
            i = 1

        # construct the list of bounding boxes and sort them from top to
        # bottom
        boundingBoxes = [cv2.boundingRect(c) for c in cnts]
        (cnts, boundingBoxes) = zip(*sorted(zip(cnts, boundingBoxes),
                                            key=lambda b: b[1][i], reverse=reverse))

        # return the list of sorted contours and bounding boxes
        return (cnts, boundingBoxes)

    def predict(self, image, type):
        rects = self.get_characters(image)
        string = []

        if type == 'text':
            for rect in rects:
                x = imread(rect, mode='L')
                #cv2.imshow('H', x)
                # x = np.invert(x)

                x = imresize(x, (28, 28))

                # x = cv2.resize(x, (28, 28))
                # reshape image data for use in neural network
                x = x.reshape(1, 28, 28, 1)

                # Convert type to float32
                x = x.astype('float32')

                # Normalize to prevent issues with model
                x /= 255

                # Predict from model
                out = self.model_text.predict(x)

                confidence = str(max(out[0]) * 100)[:6]
                predicted_char = chr(self.mapping_text[(int(np.argmax(out, axis=1)[0]))])
                # print("{} : {}".format(predicted_char, confidence))
                string.append(predicted_char)

        elif type == 'Number':
            for rect in rects:
                x = imread(rect, mode='L')
                #cv2.imshow('H', x)
                # x = np.invert(x)

                x = imresize(x, (28, 28))

                # x = cv2.resize(x, (28, 28))
                # reshape image data for use in neural network
                x = x.reshape(1, 28, 28, 1)

                # Convert type to float32
                x = x.astype('float32')

                # Normalize to prevent issues with model
                x /= 255

                # Predict from model
                out = self.model_num.predict(x)

                confidence = str(max(out[0]) * 100)[:6]
                predicted_char = chr(self.mapping_num[(int(np.argmax(out, axis=1)[0]))])
                #print("{} : {}".format(predicted_char, confidence))
                string.append(predicted_char)

        final_string = ''.join(string)
        # print(final_string)
        return final_string

    def get_characters(self, image):
        in_im = image

        im_gray = cv2.cvtColor(in_im, cv2.COLOR_BGR2GRAY)
        im_gray = cv2.GaussianBlur(im_gray, (5, 5), 0)

        # Threshold the image
        ret, im_th = cv2.threshold(im_gray, 90, 255, cv2.THRESH_BINARY_INV)
        #cv2.imshow("im", im_th)
        #cv2.waitKey(0)
        # Find contours in the image
        _, ctrs, hier = cv2.findContours(im_th.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        (ctrs, hier) = self.sort_contours(ctrs, method="left-to-right")

        # Get rectangles contains each contour
        rects = [cv2.boundingRect(ctr) for ctr in ctrs]

        APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        TEMP_FOLDER = os.path.join(APP_ROOT, 'temp_files')

        count = 0
        rect_paths = []
        for rect in rects:
            cv2.rectangle(in_im, (rect[0] - 10, rect[1] - 10), (rect[0] + rect[2] + 10, rect[1] + rect[3] + 10),
                          (0, 255, 0), 3)
            #cv2.imshow("im", in_im)
            #cv2.waitKey(0)
            new_img = im_th[rect[1] - 10:(rect[3] + rect[1] + 10), rect[0] - 10:(rect[0] + rect[2] + 10)]
            # leng = int(rect[3] * 4)
            # pt1 = int(rect[1] + rect[3] // 2 - leng // 2)
            # pt2 = int(rect[0] + rect[2] // 2 - leng // 2)
            # roi = im_th[pt1:pt1 + leng, pt2:pt2 + leng]
            final_filename = '%s/rectangle_scanned_%s.jpg' % (TEMP_FOLDER, count)
            if new_img.shape[0] and new_img.shape[1] > 4:
                cv2.imwrite(final_filename, new_img)
                rect_paths.append(final_filename)

            count = count + 1
        return rect_paths

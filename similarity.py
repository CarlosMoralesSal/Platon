import cv2
import numpy as np

def compare_images(origin,destiny,path):
    try:
        original = cv2.imread(origin)
        image_to_compare = cv2.imread(destiny)
        
        
        # 1) Check if 2 images are equals
        ##print(original.shape)
        ##print(image_to_compare.shape)
        
        width = int(original.shape[1])
        height = int(original.shape[0])
        
        dsize = (width, height)
        
        output = cv2.resize(image_to_compare, dsize)
        
        cv2.imwrite(path+"/resized.jpg",output)
        image_to_compare = cv2.imread(path+"/resized.jpg")
        print(original.shape)
        print(image_to_compare.shape)
        if original.shape == image_to_compare.shape:
            print("The images have same size and channels")
            difference = cv2.subtract(original, image_to_compare)
            b, g, r = cv2.split(difference)
        
            if cv2.countNonZero(b) == 0 and cv2.countNonZero(g) == 0 and cv2.countNonZero(r) == 0:
                print("The images are completely Equal")
            else:
                print("The images are NOT equal")
        
        # 2) Check for similarities between the 2 images
        sift = cv2.xfeatures2d.SIFT_create()
        kp_1, desc_1 = sift.detectAndCompute(original, None)
        kp_2, desc_2 = sift.detectAndCompute(image_to_compare, None)
        
        index_params = dict(algorithm=0, trees=5)
        search_params = dict()
        flann = cv2.FlannBasedMatcher(index_params, search_params)
    
        if (desc_1 is not None and desc_2 is not None) and (len(desc_1)>1 and len(desc_2)>1):
            matches = flann.knnMatch(desc_1, desc_2, k=2)
        else:
            return 0
        
        good_points = []
        for m, n in matches:
            if m.distance < 0.6*n.distance:
                good_points.append(m)
        
        # Define how similar they are
        number_keypoints = 0
        if len(kp_1) <= len(kp_2) and (len(kp_1)>0 and len(kp_2)>0):
            number_keypoints = len(kp_1)
        else:
            number_keypoints = len(kp_2)
        
        
        print("Keypoints 1ST Image: " + str(len(kp_1)))
        print("Keypoints 2ND Image: " + str(len(kp_2)))
        print("GOOD Matches:", len(good_points))
        print("How good it's the match: ", len(good_points) / number_keypoints * 100)
        

        return len(good_points) / number_keypoints * 100
    except:
        return 0.0
import json
import boto3
import requests
import uuid
import os
from PIL import Image, ExifTags
from functools import reduce
from collections import Counter
from io import BytesIO
from enum import Enum
from libs.utils import Utility

client = boto3.client(
    'rekognition',
    aws_access_key_id=os.environ['USER_AWS_ACCESS_KEY'],
    aws_secret_access_key=os.environ['USER_AWS_SECRET_KEY'] 
)

class AnalysisMethod(Enum):
    AUTO = 'auto'
    MANUAL = 'manual'

class AllowedRotation(Enum):
    ROTATE_0 = 0
    ROTATE_90 = 270
    ROTATE_180 = 180
    ROTATE_270 = 90


# returns the most optimal text to analyze
def get_most_optimal_text(found_texts):
    MIN_TEXT_LEN = 10
    MAX_REPEATED_CHARS = 6

    confidence_avg = reduce(lambda x, y: x + y['Confidence'], found_texts, 0) / len(found_texts)
    if(confidence_avg < 90):
        return 'ROTATE_0'
    else:
        # select first image that has more than one length 
        # and where its characters are not repeated many times
        for t in found_texts:
            if (len(t['DetectedText']) >= MIN_TEXT_LEN) and (t['Type'] == 'LINE'):
                if not Utility.have_repeated_characters(t['DetectedText'], MAX_REPEATED_CHARS):
                    break
        return t


def calculate_rotation(image_binary):
    try:
        response = client.detect_text(Image={'Bytes': image_binary})
        
        # get most optimal text to analyze
        selected_text = get_most_optimal_text(response['TextDetections'])
        text_polygon_vectors = selected_text['Geometry']['Polygon']
        text_bounding_box = selected_text['Geometry']['BoundingBox']
        
        # get x and y from the firts and last character
        first_char_center_x = text_polygon_vectors[0]['X']
        first_char_center_y = (text_polygon_vectors[0]['Y'] + text_polygon_vectors[3]['Y']) / 2
        last_char_center_x = text_polygon_vectors[1]['X']
        last_char_center_y = (text_polygon_vectors[1]['Y'] + text_polygon_vectors[2]['Y']) / 2

        # get the X axis of the first and second vertice of the polygon to calculate distance
        x_points = [text_polygon_vectors[0]['X'] , text_polygon_vectors[1]['X']]
        dist_x = max(x_points) - min(x_points)

        # get the Y axis of the first and second vertice of the polygon to calculate distance
        y_points = [text_polygon_vectors[0]['Y'] , text_polygon_vectors[1]['Y']]
        dist_y = max(y_points) - min(y_points)

        # proposes image rotation
        if (dist_x > dist_y): 
            if first_char_center_x <= last_char_center_x:
                return AllowedRotation.ROTATE_0.name
            else:
                return AllowedRotation.ROTATE_180.name
        else:
            if first_char_center_y <= last_char_center_y:
                return AllowedRotation.ROTATE_270.name
            else:
                return AllowedRotation.ROTATE_90.name
    except:
        return AllowedRotation.ROTATE_0.name


def suggested_orientation_in_degrees(image, force_manual_analysis):

    # get image width and height
    width, height = image.size

    print ('Image information: ')
    print ('Image Height: ' + str(height)) 
    print('Image Width: ' + str(width))    
    
    # get binary image
    image_binary = Utility.image_file_to_binary(image)
    
    # rotation auto detection by recognize
    if not force_manual_analysis:
        response = client.recognize_celebrities(Image={'Bytes': image_binary})

    # the autorotation is success
    if force_manual_analysis == False and 'OrientationCorrection' in response:
        print("exec auto analysis")
        analysis_method = AnalysisMethod.AUTO
        fix_orientation_str = response['OrientationCorrection']
    else:
        # if auto rotation is not detected
        print("exec manual analysis")
        analysis_method = AnalysisMethod.MANUAL
        fix_orientation_str = calculate_rotation(image_binary)   
    
    print('Degrees Rotation: ' + fix_orientation_str) 

    return {
        "orientation_correction": fix_orientation_str,
        "degrees_to_rotate": AllowedRotation[fix_orientation_str].value,
        "method_used": analysis_method.value
    }


def fix_orientation(event, context):

    # retrive arguments from endpoint
    try:
        image_url = Utility.get_argument(event, 'image_url')
        force_manual_analysis = Utility.get_argument(event, 'force_manual_analysis', False)
        replace_original = Utility.get_argument(event, 'replace_original', False)
    except:
        return response_template(500, { "message": "Arguments are missing or invalid" })

    # get original image
    # image = Image.open(open('examples/test-picture-8.jpeg','rb'))
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))

    # get analyzer response
    analysis_response = suggested_orientation_in_degrees(image, force_manual_analysis)
    
    # trasnform image ans store in new element
    degrees_to_rotate = analysis_response["degrees_to_rotate"]
    new_image = image.rotate(degrees_to_rotate, expand=True)
    
    # set new image to s3
    new_image_name = f'{uuid.uuid4()}.{image.format.lower()}'

    client = boto3.client(
        's3',
        aws_access_key_id=os.environ['USER_AWS_ACCESS_KEY'],
        aws_secret_access_key=os.environ['USER_AWS_SECRET_KEY']  
    )

    client.put_object(
        Body=Utility.image_file_to_binary(new_image, image.format), 
        Bucket=os.environ['S3_BUCKET_NAME'], 
        Key= new_image_name, 
        ContentType= Image.MIME[image.format]
    )

    # get url from new image
    image_url = '%s/%s/%s' % (client.meta.endpoint_url, os.environ['S3_BUCKET_NAME'], new_image_name)
    analysis_response["image_url"] = image_url

    # enpoint return
    return response_template(201, analysis_response)


def response_template(status_code, body):
    return {
        "statusCode": status_code,
        "body": json.dumps(body)
    }


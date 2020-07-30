import json
import io
from collections import Counter

class Utility(object):

    # return argumens recived on query string or raw json body
    @staticmethod
    def get_argument(event, argument_name, default_argument=None):
        
        try:
            query_arguments = event['queryStringParameters']
            if query_arguments == None: query_arguments = {}
        except: 
            query_arguments = {}

        try:
            body_arguments = json.loads(event['body'])
            if body_arguments == None: body_arguments = {}
        except: 
            body_arguments = {}

        if default_argument == None:
            return query_arguments[argument_name] if argument_name in query_arguments else body_arguments[argument_name]
        else:
            argument = query_arguments[argument_name] if argument_name in query_arguments else body_arguments.get(argument_name)
            return argument if argument != None else default_argument


    # detects if any character is repeated more than x times
    @staticmethod
    def have_repeated_characters(text, size):
        return len([i for i,j in Counter(text).items() if j>size]) > 0


    # return image in binary format
    @staticmethod
    def image_file_to_binary(image, format=False):
        # if found, preserve exif info
        if not format: format = image.format
        stream = io.BytesIO()
        if 'exif' in image.info:
            exif=image.info['exif']
            image.save(stream,format=format, exif=exif)
        else:
            image.save(stream, format=format) 

        return stream.getvalue()
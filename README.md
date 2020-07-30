# rocketpin-fix-image-rotation

Lambda function that detects the orientation of an image and corrects it if it is incorrect

## Configuration

### Env Vars

For compiling you need add **.env** file in the root directory or configure the enviroment variables on your O.S.

Example:
```
S3_BUCKET_NAME=<s3-bucket-name>
AWS_ACCESS_KEY=<s3-access-key>
AWS_SECRET_KEY=<s3-secret-key>
```

### Local invoke

Activate venv
```
source venv/bin/activate
```

Running local 
```
serverless invoke local --function fix_orientation --data '{"queryStringParameters":{"image_url": "<your-url>"}}'
```

### Deploy to AWS

```
serverless deploy
```

## Parameters

## Argument from the endpoint

* image_url: (str)[required] Directory of the image that needs to be rotated
* force_manual_analysis: (str) Bypass automatic aws rotation resolution and execute manual method
* replace_original: (boolean) Replace the original picture on S3 bucket

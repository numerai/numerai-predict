# Numerai Model Prediction Docker Environment

Presigned GET and POST urls are used to ensure that only the specified model is downloaded during execution 
and that model prediction uploads from other models are not accessed or tampered with.

## Presigned S3 model URL
The `--model` arg is designed to accept a pre-signed S3 GET URL generated via boto3
```
params = dict(Bucket='numerai-user-models', Key='integration_test')
presigned_model_url = s3_client.generate_presigned_url("get_object", params, ExpiresIn=600)
```

## Presigned S3 post URL
The `--post_url` and `--post_data` args are designed to accept a pre-signed S3 POST URL + urlencoded data dictionary
generated via boto3
```
presigned_post = s3_client.generate_presigned_post(Bucket='numerai-user-models', Key='integration_test', ExpiresIn=600)
post_url = presigned_post['url']
post_data = urllib.parse.urlencode(presigned_post['fields'])
```

## Docker container shell
You can get a shell in the container via `docker run -it --entrypoint /bin/bash numerai_predict_py3.9`


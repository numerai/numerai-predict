# Numerai Model Prediction Docker Environment

## Local testing of pickle models
You can run a local pickle model via
```
docker run -i --rm -v "$PWD:$PWD" ghcr.io/numerai/numerai_predict_py_3_10:stable --model $PWD/model.pkl
```

## Presigned S3 URLs
Presigned GET and POST urls are used to ensure that only the specified model is downloaded during execution 
and that model prediction uploads from other models are not accessed or tampered with.

The `--model` arg is designed to accept a pre-signed S3 GET URL generated via boto3
```
params = dict(Bucket='numerai-pickled-user-models',
              Key='5a5a8da7-05a4-41bf-9c2b-7f61bab5b89b/model-Kc5pT9r85SRD.pkl')
presigned_model_url = s3_client.generate_presigned_url("get_object", params, ExpiresIn=600)
```

The `--post_url` and `--post_data` args are designed to accept a pre-signed S3 POST URL + urlencoded data dictionary
generated via boto3
```
presigned_post = s3_client.generate_presigned_post(Bucket='numerai-pickled-user-models-live-output',
                                                   Key='5a5a8da7-05a4-41bf-9c2b-7f61bab5b89b/live_predictions-b7446fc4cc7e.csv',
                                                   ExpiresIn=600)
post_url = presigned_post['url']
post_data = urllib.parse.urlencode(presigned_post['fields'])
```

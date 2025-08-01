# Numerai Model Prediction Docker Environment

## Poetry vs. Requirements.txt
We prefer to do dependency management and solving through poetry because it's more sophisticated and powerful, but we also provide a requirements.txt for anyone that doesn't like to use poetry.

To convert from poetry to requirements.txt simply run:
```bash
poetry export --output requirements.txt
```

## Building the docker images locally

You can use `make` to build the docker containers on any of supported python versions:

```bash
# to build on python 3.11
make build_3_11

# if you need to force the cache to refresh
make build_3_11 DOCKER_BUILDKIT=0
```

## Local testing of pickle models
You can run a local pickle model via

```bash
docker run -i --rm -v "$PWD:$PWD" ghcr.io/numerai/numerai_predict_py_3_11:stable --debug --model $PWD/model.pkl
# optionally, you can run with --platform linux/amd64 or --platform linux/arm64 depending on host architecture
```

## Presigned S3 URLs
Presigned GET and POST urls are used to ensure that only the specified model is downloaded during execution 
and that model prediction uploads from other models are not accessed or tampered with.

The `--model` arg is designed to accept a pre-signed S3 GET URL generated via boto3

```bash
params = dict(Bucket='numerai-pickled-user-models',
              Key='5a5a8da7-05a4-41bf-9c2b-7f61bab5b89b/model-Kc5pT9r85SRD.pkl')
presigned_model_url = s3_client.generate_presigned_url("get_object", params, ExpiresIn=600)
```

The `--post_url` and `--post_data` args are designed to accept a pre-signed S3 POST URL + urlencoded data dictionary
generated via boto3

```bash
presigned_post = s3_client.generate_presigned_post(Bucket='numerai-pickled-user-models-live-output',
                                                   Key='5a5a8da7-05a4-41bf-9c2b-7f61bab5b89b/live_predictions-b7446fc4cc7e.csv',
                                                   ExpiresIn=600)
post_url = presigned_post['url']
post_data = urllib.parse.urlencode(presigned_post['fields'])
```

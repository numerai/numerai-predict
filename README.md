# Numerai Model Prediction Docker Environment

## Poetry vs. Requirements.txt
We prefer to do dependency management and solving through poetry because it's more sophisticated and powerful, but we also provide a requirements.txt for anyone that doesn't like to use poetry.

To install poetry locally, run:

```bash
curl -sSL https://install.python-poetry.org | python -
```

To convert from poetry to requirements.txt simply run:
```bash
poetry export -f requirements.txt --without-hashes --output requirements.txt

# the following regex can be applied to remove the `python_full_version` and `python_version` tags on each row:
sed -i '' 's/; .*$//g' requirements.txt
```

## Building the docker images locally

You can use `make` to build the docker containers on any of supported python versions:

```bash
# to build on python 3.13
make build_3_13

# if you need to force the cache to refresh
make build_3_13 DOCKER_BUILDKIT=0
```

## Local testing of pickle models
You can run a local pickle model via

```bash
docker run -i --rm -v "$PWD:$PWD" ghcr.io/numerai/numerai_predict_py_3_13:stable --debug --model $PWD/model.pkl
# optionally, you can run with --platform linux/amd64 or --platform linux/arm64 depending on host architecture
```

## Classic v6 model contract

The dataset and benchmark defaults use `v6.0`. V6 is the same data as Signals v3.1:
tickers and dates are columns, not the parquet row index. Train on numeric features;
`feature_country` is text. Benchmark inputs also contain `numerai_ticker` and `date`.
Align benchmarks by those keys when using them in a model.

Return a DataFrame containing predictions between 0 and 1, preserving every input
row index exactly once. Reordering rows is allowed if their index labels stay intact.
The runner attaches `numerai_ticker` and `date` by index for live submissions and
historical diagnostics. If the model returns either identity column itself, it must
match the corresponding input row. Do not reset the index after reordering predictions.

```python
def predict(live_features):
    scores = model.predict(live_features[feature_cols])
    return pd.Series(scores, index=live_features.index).rank(pct=True).to_frame("prediction")
```

Legacy ID-indexed inputs keep their existing output format. While v5 live files remain
available, select both legacy paths explicitly with `--dataset v5.3/live.parquet`
and `--benchmarks v5.3/live_benchmark_models.parquet`; a v5-trained model is not
compatible with v6 simply because it unpickles successfully.

## Testing and releasing v6

`make test` runs the prediction suite in the shell image and every supported Python
image. Tests serialize v6 models in each runtime and exercise local parquet inputs,
including one- and two-argument models, ticker/date output, and legacy pickle fixtures.
They do not depend on retired public training data or external live downloads.

After approval, deploy to the `staging` branch to publish versioned and `latest`
images to staging ECR through `deploy-images.yml`. Test those exact images through
Model Uploads, including historical diagnostics, before production activation.
Merging to `master` publishes to production ECR and GHCR. Coordinate it with the
data release; changing defaults is not permission to activate v6 early.

Image publication alone does not select a runtime for hosted users. Update the
tournament repository's image definitions and `compute_pickle_docker_images` rows,
test every selectable runtime, and record image tags/digests before changing defaults.
The tournament repository's Model Uploads maintenance guide owns that rollout.

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

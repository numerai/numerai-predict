import argparse
import logging
import os
import pickle
import requests
import secrets
import shutil
import sys
import urllib
import time
import random
import io
from typing import Callable
from inspect import signature

from numerapi import NumerAPI
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        default="v5.0/live.parquet",
        help="Numerapi dataset path or local file.",
    )
    parser.add_argument(
        "--benchmarks",
        default="v5.0/live_benchmark_models.parquet",
        help="Numerapi benchmark model path or local file.",
    )
    parser.add_argument("--model", required=True, help="Pickled model file or URL")
    parser.add_argument("--output_dir", default="/tmp", help="File output dir")
    parser.add_argument("--post_url", help="Url to post model output")
    parser.add_argument("--post_data", help="Urlencoded post data dict")
    parser.add_argument("--debug", action="store_true", help="Enable DEBUG log level")
    args = parser.parse_args()

    if args.post_url and not args.post_data:
        raise argparse.ArgumentError(
            "--post_data arg is required when using --post_url"
        )

    if args.post_data and not args.post_url:
        raise argparse.ArgumentError(
            "--post_url arg is required when using --post_data"
        )

    if not os.path.isdir(args.output_dir):
        raise argparse.ArgumentError(
            f"--output_dir {args.output_dir} is not an existing directory"
        )

    if args.post_data:
        data = urllib.parse.parse_qs(args.post_data)
        if type(data) != dict:
            raise argparse.ArgumentError(
                "--post_data must be urlencoded and resolve to dict"
            )
        args.post_data = data

    return args


def py_version(separator="."):
    return separator.join(sys.version.split(".")[:2])


def exit_with_help(error):
    git_ref = os.getenv("GIT_REF", "latest")
    docker_image_path = (
        f"ghcr.io/numerai/numerai_predict_py_{py_version('_')}:{git_ref}"
    )
    docker_args = "--debug --model $PWD/[PICKLE_FILE]"

    logging.root.handlers[0].flush()
    logging.root.handlers[0].setFormatter(logging.Formatter("%(message)s"))

    logging.info(
        f"""
{"-" * 80}
Debug your pickle model locally via docker command:

    docker run -i --rm -v "$PWD:$PWD" {docker_image_path} {docker_args}

Try our other support resources:
    [Github]  https://github.com/numerai/numerai-predict
    [Discord] https://discord.com/channels/894652647515226152/1089652477957246996
{"-" * 80}"""
    )

    sys.exit(error)


def retry_request_with_backoff(
    request_func: Callable[[], requests.Response],
    retries: int = 10,
    delay_base: float = 1.5,
    delay_exp: float = 1.5,
):
    delay_base = max(1.1, delay_base)
    delay_exp = max(1.1, delay_exp)
    curr_delay = delay_base
    for i in range(retries):
        try:
            response = request_func()
            logging.info("HTTP Response Status: %s", response.status_code)
            if response.status_code >= 500:
                logging.error("Encountered Server Error. Retrying...")
                time.sleep(curr_delay)
                curr_delay **= random.uniform(1, delay_exp)
            elif 200 <= response.status_code < 300:
                logging.debug("Request successful! Returning...")
                return response
            else:
                raise RuntimeError(f"HTTP Error {response.reason} - {response.text}")
        except requests.exceptions.ConnectionError:
            logging.error("Connection reset! Retrying...")
            time.sleep(curr_delay)
            curr_delay **= random.uniform(1, delay_exp)
            continue
        except requests.exceptions.SSLError as e:
            logging.error("SSL Error: %s", e)
        finally:
            logging.info("Retrying in %s seconds...", curr_delay)
            time.sleep(curr_delay)
            curr_delay **= random.uniform(1, delay_exp)
    raise RuntimeError(f"Could not complete function call after {retries} retries...")


def get_data(dataset, output_dir):
    if os.path.exists(dataset):
        dataset_path = dataset
        logging.info("Using local %s for live data", dataset_path)
    elif dataset.startswith("/"):
        logging.error("Local dataset not found - %s does not exist!", dataset)
        exit_with_help(1)
    else:
        dataset_path = os.path.join(output_dir, dataset)
        logging.info("Using NumerAPI to download %s for live data", dataset)
        napi = NumerAPI()
        napi.download_dataset(dataset, dataset_path)
    logging.info("Loading live features %s", dataset_path)
    live_features = pd.read_parquet(dataset_path)
    return live_features


def upload_live_output(
    predictions: pd.DataFrame,
    post_url: str,
    post_data: str,
    predictions_csv_file_name: str,
):
    logging.info("Uploading predictions to %s", post_url)
    csv_buffer = io.StringIO()
    predictions.to_csv(csv_buffer)

    def post_live_output():
        csv_buffer.seek(0)
        return requests.post(
            post_url,
            data=post_data,
            files={"file": (predictions_csv_file_name, csv_buffer, "text/csv")},
        )

    retry_request_with_backoff(post_live_output)


def main(args):
    logging.getLogger().setLevel(logging.DEBUG if args.debug else logging.INFO)

    logging.info(
        "Running numerai-predict:%s - Python %s", os.getenv("GIT_REF"), py_version()
    )

    if args.model.lower().startswith("http"):
        truncated_url = args.model.split("?")[0]
        logging.info("Downloading model %s", truncated_url)
        response = retry_request_with_backoff(
            lambda: requests.get(args.model, stream=True, allow_redirects=True)
        )
        model_name = truncated_url.split("/")[-1]
        model_pkl = os.path.join(args.output_dir, model_name)
        logging.info("Saving model to %s", model_pkl)
        with open(model_pkl, "wb") as f:
            shutil.copyfileobj(response.raw, f)
    else:
        model_pkl = args.model

    logging.info("Loading model %s", model_pkl)
    try:
        model = pd.read_pickle(model_pkl)
    except pickle.UnpicklingError as e:
        logging.error("Invalid pickle - %s", e)
        if args.debug:
            logging.exception(e)
        exit_with_help(1)
    except TypeError as e:
        logging.error("Pickle incompatible with %s", py_version())
        if args.debug:
            logging.exception(e)
        exit_with_help(1)
    except ModuleNotFoundError as e:
        logging.error("Import error reading pickle - %s", e)
        if args.debug:
            logging.exception(e)
        exit_with_help(1)
    logging.debug(model)

    num_args = len(signature(model).parameters)

    live_features = get_data(args.dataset, args.output_dir)
    if num_args > 1:
        benchmark_models = get_data(args.benchmarks, args.output_dir)

    logging.info("Predicting on %s rows of live features", len(live_features))
    try:
        if num_args == 1:
            predictions = model(live_features)
        elif num_args == 2:
            predictions = model(live_features, benchmark_models)
        else:
            logging.error(
                "Invalid pickle function - %s must have 1 or 2 arguments", model_pkl
            )
            exit_with_help(1)

        if predictions is None:
            logging.error("Pickle function is invalid - returned None")
            exit_with_help(1)
        elif type(predictions) != pd.DataFrame:
            logging.error(
                "Pickle function is invalid - returned %s instead of pd.DataFrame",
                type(predictions),
            )
            exit_with_help(1)
        elif len(predictions) == 0:
            logging.error("Pickle function returned 0 predictions")
            exit_with_help(1)
        elif predictions.isna().any().any():
            logging.error("Pickle function returned at least 1 NaN prediction")
            exit_with_help(1)
        elif not (predictions.iloc[:, 0].between(0, 1).all().all()):
            logging.error(
                "Pickle function returned invalid predictions. Ensure values are between 0 and 1."
            )
            exit_with_help(1)
    except TypeError as e:
        logging.error("Pickle function is invalid - %s", e)
        if args.debug:
            logging.exception(e)
        exit_with_help(1)
    except Exception as e:
        logging.exception(e)
        exit_with_help(1)

    logging.info("Generated %s predictions", len(predictions))
    logging.debug(predictions)

    predictions_csv_file_name = os.path.join(
        args.output_dir, f"live_predictions-{secrets.token_hex(6)}.csv"
    )
    if args.post_url:
        upload_live_output(
            predictions,
            args.post_url,
            args.post_data,
            predictions_csv_file_name,
        )
    else:
        logging.info("Saving predictions to %s", predictions_csv_file_name)
        with open(predictions_csv_file_name, "w") as f:
            predictions.to_csv(f)


if __name__ == "__main__":
    main(parse_args())

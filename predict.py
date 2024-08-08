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
import glob
from inspect import signature

from numerapi import NumerAPI
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        default="v4.3/live_int8.parquet",
        help="Numerapi dataset path or local file.",
    )
    parser.add_argument(
        "--benchmarks",
        default="v4.3/live_benchmark_models.parquet",
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
    url: str,
    retries: int = 10,
    delay_base: float = 1.5,
    delay_exp: float = 1.5,
    retry_on_status_codes: list[int] = [503],
    debug: bool = False,
):
    delay_base = max(1.1, delay_base)
    delay_exp = max(1.1, delay_exp)
    curr_delay = delay_base
    for i in range(retries):
        try:
            response = requests.get(url, stream=True, allow_redirects=True)
        except requests.exceptions.ConnectionError:
            logging.error("Connection reset! Retrying...")
            time.sleep(curr_delay)
            curr_delay **= random.uniform(1, delay_exp)
            continue
        if response.status_code in retry_on_status_codes:
            if debug:
                logging.debug(f"Recieved status {response.status_code}. Retrying...")
            time.sleep(curr_delay)
            curr_delay **= random.uniform(1, delay_exp)
        elif response.status_code != 200:
            logging.error(f"{response.reason} {response.text}")
            sys.exit(1)
        else:
            logging.debug(f"Request successful! Returning...")
            return response
    raise RuntimeError(f"Could not complete function call after {retries} retries...")


def get_data(dataset, output_dir):
    if os.path.exists(dataset):
        dataset_path = dataset
        logging.info(f"Using local {dataset_path} for live data")
    elif dataset.startswith("/"):
        logging.error(f"Local dataset not found - {dataset} does not exist!")
        exit_with_help(1)
    else:
        dataset_path = os.path.join(output_dir, dataset)
        logging.info(f"Using NumerAPI to download {dataset} for live data")
        napi = NumerAPI()
        napi.download_dataset(dataset, dataset_path)
    logging.info(f"Loading live features {dataset_path}")
    live_features = pd.read_parquet(dataset_path)
    return live_features


def main(args):
    logging.getLogger().setLevel(logging.DEBUG if args.debug else logging.INFO)

    logging.info(f"Running numerai-predict:{os.getenv('GIT_REF')} Python{py_version()}")

    if args.model.lower().startswith("http"):
        truncated_url = args.model.split("?")[0]
        logging.info(f"Downloading model {truncated_url}")
        response = retry_request_with_backoff(args.model)
        model_name = truncated_url.split("/")[-1]
        model_pkl = os.path.join(args.output_dir, model_name)
        logging.info(f"Saving model to {model_pkl}")
        with open(model_pkl, "wb") as f:
            shutil.copyfileobj(response.raw, f)
    else:
        model_pkl = args.model

    logging.info(f"Loading model {model_pkl}")
    try:
        model = pd.read_pickle(model_pkl)
    except pickle.UnpicklingError as e:
        logging.error(f"Invalid pickle - {e}")
        if args.debug:
            logging.exception(e)
        exit_with_help(1)
    except TypeError as e:
        logging.error(f"Pickle incompatible with {py_version()}")
        logging.exception(e) if args.debug else logging.error(e)
        exit_with_help(1)
    except ModuleNotFoundError as e:
        logging.error(f"Import error reading pickle - {e}")
        if args.debug:
            logging.exception(e)
        exit_with_help(1)
    logging.debug(model)

    num_args = len(signature(model).parameters)

    live_features = get_data(args.dataset, args.output_dir)
    if num_args > 1:
        benchmark_models = get_data(args.benchmarks, args.output_dir)

    logging.info(f"Predicting on {len(live_features)} rows of live features")
    try:
        if num_args == 1:
            predictions = model(live_features)
        elif num_args == 2:
            predictions = model(live_features, benchmark_models)
        else:
            logging.error(
                f"Invalid pickle function - {model_pkl} must have 1 or 2 arguments"
            )
            exit_with_help(1)

        if predictions is None:
            logging.error("Pickle function is invalid - returned None")
            exit_with_help(1)
        elif type(predictions) != pd.DataFrame:
            logging.error(
                f"Pickle function is invalid - returned {type(predictions)} instead of pd.DataFrame"
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
        logging.error(f"Pickle function is invalid - {e}")
        if args.debug:
            logging.exception(e)
        exit_with_help(1)
    except Exception as e:
        logging.exception(e)
        exit_with_help(1)

    logging.info(f"Generated {len(predictions)} predictions")
    logging.debug(predictions)

    predictions_csv = os.path.join(
        args.output_dir, f"live_predictions-{secrets.token_hex(6)}.csv"
    )
    logging.info(f"Saving predictions to {predictions_csv}")
    with open(predictions_csv, "w") as f:
        predictions.to_csv(f)

    if args.post_url:
        logging.info(f"Uploading predictions to {args.post_url}")
        files = {"file": open(predictions_csv, "rb")}

        MAX_RETRIES = 5
        RETRY_DELAY = 1.5
        RETRY_EXP = 1.5
        for i in range(MAX_RETRIES):
            r = requests.post(args.post_url, data=args.post_data, files=files)
            if r.status_code >= 500:
                logging.info("Encountered S3 Server Error.")
            elif r.status_code not in [200, 204]:
                logging.info(f"HTTP Response Status: {r.status_code}")
                logging.error(r.reason)
                logging.error(r.text)
            else:
                sys.exit(0)
            time.sleep(RETRY_DELAY)
            RETRY_DELAY **= random.uniform(1, RETRY_EXP)


if __name__ == "__main__":
    main(parse_args())

import argparse
import logging
import os
import requests
import secrets
import shutil
import sys
import tempfile
import urllib

from numerapi import NumerAPI
import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", default="v4.1/live.parquet", help="Numerapi dataset path"
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
                f"--post_data must be urlencoded and resolve to dict"
            )
        args.post_data = data

    logging.getLogger().setLevel(logging.DEBUG if args.debug else logging.INFO)

    return args


def predict(args):
    if args.model.lower().startswith("http"):
        logging.info(f"Downloading model {args.model}")
        response = requests.get(args.model, stream=True, allow_redirects=True)
        if response.status_code != 200:
            logging.error(f"{response.reason} {response.text}")
            sys.exit(1)

        model_pkl = os.path.join(args.output_dir, f"model-{secrets.token_hex(6)}.pkl")
        logging.info(f"Saving model to {model_pkl}")
        with open(model_pkl, "wb") as f:
            shutil.copyfileobj(response.raw, f)
    else:
        model_pkl = args.model

    logging.info(f"Loading model {model_pkl}")
    model = pd.read_pickle(model_pkl)
    logging.debug(model)

    napi = NumerAPI()
    current_round = napi.get_current_round()

    dataset_path = os.path.join(args.output_dir, args.dataset)
    logging.info(f"Downloading {args.dataset} for round {current_round}")
    napi.download_dataset(args.dataset, dataset_path)

    logging.info(f"Loading live features {dataset_path}")
    live_features = pd.read_parquet(dataset_path)

    logging.info(f"Predicting on {len(live_features)} live features")
    predictions = model(live_features)

    logging.info(f"Generated {len(predictions)} predictions")
    logging.debug(predictions)

    predictions_csv = os.path.join(
        args.output_dir, f"live_predictions_{current_round}-{secrets.token_hex(6)}.csv"
    )
    logging.info(f"Saving predictions to {predictions_csv}")
    with open(predictions_csv, "w") as f:
        predictions.to_csv(f)

    if args.post_url:
        logging.info(f"Uploading predictions to {args.post}")
        files = {"file": open(predictions_csv, "rb")}
        r = requests.post(args.post_url, data=args.post_data, files=files)
        if r.status_code != 200:
            logging.error(f"{r.status_code} {r.reason} {r.text}")
            sys.exit(1)
        logging.info(r.status_code)


if __name__ == "__main__":
    predict(parse_args())

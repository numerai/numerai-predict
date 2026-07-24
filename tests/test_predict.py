"""
Set up python unittests for the predict module
"""

import argparse
import unittest
from unittest import mock

import predict

import pandas as pd


class TestPredict(unittest.TestCase):
    def setUp(self):
        pass

    def test__is_python_version_pickle_error(self):
        self.assertTrue(
            predict.is_python_version_pickle_error(
                ValueError("unsupported pickle protocol: 5")
            )
        )
        self.assertTrue(
            predict.is_python_version_pickle_error(
                TypeError("code expected at most 18 arguments, got 21")
            )
        )
        self.assertTrue(
            predict.is_python_version_pickle_error(
                ValueError("bad marshal data (unknown type code)")
            )
        )
        self.assertFalse(
            predict.is_python_version_pickle_error(
                ModuleNotFoundError("No module named 'xgboost'")
            )
        )

    def test__retry_request_with_backoff_bad_callable_return(self):
        self.assertRaises(
            AttributeError,
            predict.retry_request_with_backoff,
            lambda: "not a response object",
        )

    def test__upload_live_output(self):
        post_mock = mock.MagicMock()
        predict.requests.post = post_mock

        post_url_str = "http://example.com"
        data_dict = {"post": "data"}
        filename_str = "predictions.csv"

        post_calls = []
        response_statuses = [500, 200]

        def check_inputs(post_url, data, files):
            assert post_url == post_url_str
            assert data == data_dict
            assert files == {"file": (filename_str, mock.ANY, "text/csv")}
            post_calls.append(files["file"][1])
            response_mock = mock.MagicMock()
            response_mock.status_code = response_statuses[len(post_calls) - 1]
            return response_mock

        post_mock.side_effect = check_inputs

        with mock.patch("predict.time.sleep", return_value=None):
            predict.upload_live_output(
                pd.DataFrame({"column": [1, 2, 3]}),
                post_url_str,
                data_dict,
                filename_str,
            )

        assert len(post_calls) == len(response_statuses)
        assert all(buffer.seekable() for buffer in post_calls)
        assert post_calls[0] is not post_calls[1]

    def test__main_exits_with_help_on_python_version_pickle_mismatch(self):
        args = argparse.Namespace(
            dataset="v5.2/live.parquet",
            benchmarks="v5.2/live_benchmark_models.parquet",
            model="model.pkl",
            output_dir="/tmp",
            post_url=None,
            post_data=None,
            debug=False,
        )

        with (
            mock.patch(
                "predict.pd.read_pickle",
                side_effect=ValueError("unsupported pickle protocol: 5"),
            ),
            mock.patch("predict.exit_with_help", side_effect=SystemExit(1)),
            mock.patch("predict.logging.error") as logging_error,
        ):
            with self.assertRaises(SystemExit):
                predict.main(args)

        logging_error.assert_called_once_with(
            "Pickle could not be loaded in Python %s. It was likely created with a different Python version. Recreate the pickle with Python %s or submit it to the matching numerai-predict image.",
            predict.py_version(),
            predict.py_version(),
        )

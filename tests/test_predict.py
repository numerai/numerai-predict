"""
Set up python unittests for the predict module
"""

import unittest
from unittest import mock

import predict

import pandas as pd


class TestPredict(unittest.TestCase):
    def setUp(self):
        pass

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

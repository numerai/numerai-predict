"""
Set up python unittests for the predict module
"""

import argparse
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import predict

import pandas as pd
import cloudpickle


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
            dataset="v6.0/live.parquet",
            benchmarks="v6.0/live_benchmark_models.parquet",
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

    def run_model(self, features, model):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(
                dataset="live.parquet",
                benchmarks="live_benchmark_models.parquet",
                model="model.pkl",
                output_dir=directory,
                post_url=None,
                post_data=None,
                debug=False,
            )
            with (
                mock.patch("predict.pd.read_pickle", return_value=model),
                mock.patch("predict.get_data", return_value=features),
            ):
                predict.main(args)
            return pd.read_csv(next(Path(directory).glob("live_predictions-*.csv")))

    def test_v6_output_keeps_ticker_and_date_when_predictions_are_reordered(self):
        features = pd.DataFrame(
            {"numerai_ticker": ["A US", "B US"], "date": ["2026-01-02"] * 2},
            index=[7, 9],
        )

        def model(live_features):
            return pd.DataFrame({"prediction": [0.8, 0.2]}, index=[9, 7])

        output = self.run_model(features, model)
        self.assertEqual(output["numerai_ticker"].tolist(), ["B US", "A US"])
        self.assertEqual(output["date"].tolist(), ["2026-01-02"] * 2)
        self.assertEqual(output["prediction"].tolist(), [0.8, 0.2])

    def test_v6_two_argument_model_can_return_identity_columns_first(self):
        features = pd.DataFrame(
            {"numerai_ticker": ["A US", "B US"], "date": ["2026-01-02"] * 2}
        )

        def model(live_features, benchmarks):
            pd.testing.assert_frame_equal(benchmarks, features)
            return live_features.assign(prediction=[0.2, 0.8])

        output = self.run_model(features, model)
        self.assertEqual(output["numerai_ticker"].tolist(), ["A US", "B US"])
        self.assertEqual(output["prediction"].tolist(), [0.2, 0.8])

    def test_v6_identity_survives_model_mutating_its_features(self):
        features = pd.DataFrame(
            {"numerai_ticker": ["A US", "B US"], "date": ["2026-01-02"] * 2}
        )

        def model(live_features):
            live_features.drop(columns=["numerai_ticker", "date"], inplace=True)
            return pd.DataFrame({"prediction": [0.2, 0.8]}, index=live_features.index)

        output = self.run_model(features, model)
        self.assertEqual(output["numerai_ticker"].tolist(), ["A US", "B US"])

    def test_v6_rejects_missing_duplicate_or_unknown_row_indexes(self):
        features = pd.DataFrame(
            {"numerai_ticker": ["A US", "B US"], "date": ["2026-01-02"] * 2}
        )
        for index in ([0], [0, 0], [0, 2]):
            with self.subTest(index=index):

                def model(live_features):
                    return pd.DataFrame({"prediction": [0.5] * len(index)}, index=index)

                with self.assertRaises(SystemExit):
                    self.run_model(features, model)

    def test_v6_rejects_conflicting_ticker_metadata(self):
        features = pd.DataFrame(
            {"numerai_ticker": ["A US", "B US"], "date": ["2026-01-02"] * 2}
        )

        def model(live_features):
            return pd.DataFrame(
                {"prediction": [0.2, 0.8], "numerai_ticker": ["B US", "A US"]}
            )

        with self.assertRaises(SystemExit):
            self.run_model(features, model)

    def test_v5_output_keeps_legacy_id_index(self):
        features = pd.DataFrame(
            {"feature_a": [1, 2]}, index=pd.Index(["n1", "n2"], name="id")
        )

        def model(live_features):
            return pd.DataFrame({"prediction": [0.2, 0.8]}, index=live_features.index)

        output = self.run_model(features, model)
        self.assertEqual(
            output.to_dict("list"), {"id": ["n1", "n2"], "prediction": [0.2, 0.8]}
        )

    def test_v6_serialized_models_with_local_parquet_inputs(self):
        features = pd.DataFrame(
            {
                "numerai_ticker": ["A US", "B US"],
                "date": ["2026-01-02"] * 2,
                "feature_numeric": [0.2, 0.8],
                "feature_country": ["US", "US"],
            }
        )
        benchmarks = features[["numerai_ticker", "date"]].assign(
            lgbm_jupiter_60=[0.3, 0.7]
        )

        def one_arg(live_features):
            return live_features[["feature_numeric"]].rename(
                columns={"feature_numeric": "prediction"}
            )

        def two_args(live_features, live_benchmarks):
            return live_benchmarks[["lgbm_jupiter_60"]].rename(
                columns={"lgbm_jupiter_60": "prediction"}
            )

        for model, expected in ((one_arg, [0.2, 0.8]), (two_args, [0.3, 0.7])):
            with self.subTest(model=model.__name__):
                output = self.run_serialized_model(
                    features, benchmarks, cloudpickle.dumps(model)
                )
                self.assertEqual(output["prediction"].tolist(), expected)
                self.assertEqual(output["numerai_ticker"].tolist(), ["A US", "B US"])
                self.assertEqual(output["date"].tolist(), ["2026-01-02"] * 2)

    def test_existing_runtime_pickles_with_legacy_inputs(self):
        version = f"{sys.version_info.major}_{sys.version_info.minor}"
        for path in (Path(__file__).parent / "models").glob(f"model_{version}*.pkl"):
            with self.subTest(pickle=path.name):
                model = pd.read_pickle(path)
                # Existing fixtures are LightGBM models trained on v5 features.
                features = pd.DataFrame(
                    0.5,
                    columns=model.__globals__["features"],
                    index=pd.Index(["n1", "n2"], name="id"),
                )
                output = self.run_serialized_model(
                    features, pd.DataFrame(index=features.index), path.read_bytes()
                )
                self.assertEqual(output["id"].tolist(), ["n1", "n2"])
                self.assertTrue(output["prediction"].between(0, 1).all())

    def run_serialized_model(self, features, benchmarks, model_bytes):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            features.to_parquet(root / "live.parquet")
            benchmarks.to_parquet(root / "benchmarks.parquet")
            (root / "model.pkl").write_bytes(model_bytes)
            args = argparse.Namespace(
                dataset=str(root / "live.parquet"),
                benchmarks=str(root / "benchmarks.parquet"),
                model=str(root / "model.pkl"),
                output_dir=directory,
                post_url=None,
                post_data=None,
                debug=False,
            )
            predict.main(args)
            return pd.read_csv(next(root.glob("live_predictions-*.csv")))

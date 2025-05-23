#################################################################################
# The Institute for the Design of Advanced Energy Systems Integrated Platform
# Framework (IDAES IP) was produced under the DOE Institute for the
# Design of Advanced Energy Systems (IDAES).
#
# Copyright (c) 2018-2024 by the software owners: The Regents of the
# University of California, through Lawrence Berkeley National Laboratory,
# National Technology & Engineering Solutions of Sandia, LLC, Carnegie Mellon
# University, West Virginia University Research Corporation, et al.
# All rights reserved.  Please see the files COPYRIGHT.md and LICENSE.md
# for full copyright and license information.
#################################################################################

from importlib import resources
from numbers import Number
from pathlib import Path
from typing import Dict, Union
import os

import pytest

from idaes.apps.grid_integration import DoubleLoopCoordinator
from idaes.apps.grid_integration.tests.util import (
    make_testing_tracker,
    make_testing_bidder,
)

## create trackers
thermal_tracker = make_testing_tracker()
thermal_projection_tracker = make_testing_tracker()
thermal_bidder = make_testing_bidder()

# create coordinator
coordinator = DoubleLoopCoordinator(
    bidder=thermal_bidder,
    tracker=thermal_tracker,
    projection_tracker=thermal_projection_tracker,
)

# define custom type for type hinting
PrescientOptions = Dict[str, Union[str, bool, Number, dict]]


class TestDoubleLoopIntegration:
    "Integration test for the double loop using 5bus use case."

    @pytest.fixture
    def data_path(self) -> Path:
        # NOTE here we want the path to the entire 5bus directory
        # we need to specify __init__.py and then use `pathlib.Path.parent` since
        # `importlib.resources.as_path()` only supports directories on Python 3.12+
        with resources.as_file(
            resources.files("idaes.tests.prescient.5bus").joinpath("__init__.py")
        ) as pkg_file:
            return pkg_file.parent

    @pytest.mark.unit
    def test_data_path_available(self, data_path: Path):
        assert data_path.is_dir()

    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        path = tmp_path / "bidder_integration_test_output"
        path.mkdir()
        return path

    @pytest.fixture
    def self_scheduler_output_dir(self, tmp_path: Path) -> Path:
        path = tmp_path / "self_scheduler_integration_test_output"
        path.mkdir()
        return path

    @pytest.fixture
    def self_scheduler_plugin_path(self) -> Path:
        with resources.as_file(
            resources.files("idaes.apps.grid_integration.tests").joinpath(
                "self_scheduler_integration_test_plugin.py"
            )
        ) as p:
            return Path(p)

    @pytest.mark.unit
    def test_self_scheduler_plugin_path_is_existing_file(
        self, self_scheduler_plugin_path
    ):
        assert self_scheduler_plugin_path.is_file()

    @pytest.fixture
    def prescient_options(self, data_path: Path) -> PrescientOptions:
        return {
            "data_path": str(data_path),
            "input_format": "rts-gmlc",
            "simulate_out_of_sample": True,
            "run_sced_with_persistent_forecast_errors": True,
            "start_date": "07-10-2020",
            "num_days": 2,
            "sced_horizon": 4,
            "ruc_mipgap": 0.01,
            "reserve_factor": 0.0,
            "deterministic_ruc_solver": "cbc",
            "day_ahead_pricing": "LMP",
            "symbolic_solver_labels": True,
            "deterministic_ruc_solver_options": {
                "feas": "off",
                "DivingF": "on",
            },
            "sced_solver": "cbc",
            "sced_frequency_minutes": 60,
            "ruc_horizon": 48,
            "compute_market_settlements": True,
            "monitor_all_contingencies": False,
            "output_solver_logs": False,
            "price_threshold": 1000,
            "contingency_price_threshold": 100,
            "reserve_price_threshold": 5,
        }

    @pytest.fixture
    def bidder_sim_options(
        self,
        prescient_options,
        output_dir: Path,
    ) -> PrescientOptions:
        prescient_options["plugin"] = {
            "doubleloop": {
                "module": coordinator.prescient_plugin_module,
                "bidding_generator": "10_STEAM",
            }
        }
        prescient_options["output_directory"] = str(output_dir)
        return prescient_options

    @pytest.fixture
    def self_scheduler_sim_options(
        self,
        prescient_options,
        self_scheduler_output_dir: Path,
        self_scheduler_plugin_path: Path,
    ) -> PrescientOptions:
        prescient_options["plugin"] = {
            "doubleloop": {
                "module": str(self_scheduler_plugin_path),
                "bidding_generator": "10_STEAM",
            }
        }
        prescient_options["output_directory"] = str(self_scheduler_output_dir)
        return prescient_options

    @pytest.fixture
    def run_bidder_simulator(self, bidder_sim_options: PrescientOptions) -> None:
        prescient_simulator = pytest.importorskip(
            "prescient.simulator",
            reason="Prescient (optional dependency) not available",
        )

        prescient_simulator.Prescient().simulate(**bidder_sim_options)

    @pytest.fixture
    def run_self_scheduler_simulator(
        self, self_scheduler_sim_options: PrescientOptions
    ) -> None:
        prescient_simulator = pytest.importorskip(
            "prescient.simulator",
            reason="Prescient (optional dependency) not available",
        )

        prescient_simulator.Prescient().simulate(**self_scheduler_sim_options)

    @pytest.fixture
    def simulation_results_dir(self, run_bidder_simulator, output_dir):
        return output_dir

    @pytest.fixture
    def self_scheduler_simulation_results_dir(
        self, run_self_scheduler_simulator, self_scheduler_output_dir
    ):
        return self_scheduler_output_dir

    @pytest.mark.integration
    def test_prescient_outputs_exist(
        self, simulation_results_dir, self_scheduler_simulation_results_dir
    ):
        assert os.path.isdir(simulation_results_dir)
        assert os.path.isdir(self_scheduler_simulation_results_dir)

        file_names = [
            "hourly_gen_summary.csv",
            "tracker_detail.csv",
            "hourly_summary.csv",
            "bus_detail.csv",
            "overall_simulation_output.csv",
            "virtual_detail.csv",
            "bidding_model_detail.csv",
            "bidder_detail.csv",
            "daily_summary.csv",
            "line_detail.csv",
            "thermal_detail.csv",
            "runtimes.csv",
            "tracking_model_detail.csv",
            "renewables_detail.csv",
            "contingency_detail.csv",
        ]

        for f in file_names:
            file_path = os.path.join(simulation_results_dir, f)
            assert os.path.isfile(file_path)

            file_path = os.path.join(self_scheduler_simulation_results_dir, f)
            assert os.path.isfile(file_path)

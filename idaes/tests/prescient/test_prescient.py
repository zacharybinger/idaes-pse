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

import pytest
import pandas as pd


# define custom type for type hinting
PrescientOptions = Dict[str, Union[str, bool, Number, dict]]


class Test5Bus:
    "Simple test using 5bus use case"

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
        path = tmp_path / "5bus_output"
        path.mkdir()
        return path

    @pytest.fixture
    def prescient_options(self, data_path: Path, output_dir: Path) -> PrescientOptions:
        return {
            "data_path": str(data_path),
            "input_format": "rts-gmlc",
            "simulate_out_of_sample": True,
            "run_sced_with_persistent_forecast_errors": True,
            "output_directory": str(output_dir),
            "start_date": "07-10-2020",
            "num_days": 2,
            "sced_horizon": 1,
            "ruc_mipgap": 0.01,
            "reserve_factor": 0.1,
            "deterministic_ruc_solver": "cbc",
            "deterministic_ruc_solver_options": {
                "feas": "off",
                "DivingF": "on",
            },
            "sced_solver": "cbc",
            "sced_frequency_minutes": 60,
            "ruc_horizon": 36,
            "compute_market_settlements": True,
            "monitor_all_contingencies": False,
            "output_solver_logs": False,
            "price_threshold": 1000,
            "contingency_price_threshold": 100,
            "reserve_price_threshold": 5,
        }

    @pytest.fixture
    def run_simulator(self, prescient_options: PrescientOptions) -> None:
        prescient_simulator = pytest.importorskip(
            "prescient.simulator",
            reason="Prescient (optional dependency) not available",
        )

        sim = prescient_simulator.Prescient()
        sim.simulate(**prescient_options)

    @pytest.fixture
    def simulation_results_table(
        self,
        run_simulator,
        output_dir: Path,
        name: str = "overall_simulation_output.csv",
    ) -> pd.DataFrame:

        path = output_dir / name
        return pd.read_csv(path)

    @pytest.mark.component
    # TODO use a more specific test to validate simulation output
    def test_simulation_results(self, simulation_results_table: pd.DataFrame):
        assert not simulation_results_table.empty

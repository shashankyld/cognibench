from os import getcwd
import pandas as pd
import numpy as np
import time
from ldmunit.testing.tests import MSETest, MAETest, CrossEntropyTest
from ldmunit.models import CACO
from ldmunit.capabilities import Interactive
from sciunit import TestSuite
from sciunit import settings as sciunit_settings

from model_defs import BEASTsdPython, BEASTsdOctave, BEASTsdR

sciunit_settings["CWD"] = getcwd()


def get_models(python_model_IDs, octave_model_IDs, r_model_IDs):
    folder_fmt = "beastsd_contestant_{}"
    model_name_fmt = "Contestant {} ({})"
    python_models = [
        BEASTsdPython(
            import_base_path=folder_fmt.format(i),
            name=model_name_fmt.format(i, "Python"),
        )
        for i in python_model_IDs
    ]
    octave_models = [
        BEASTsdOctave(
            import_base_path=folder_fmt.format(i),
            name=model_name_fmt.format(i, "Octave"),
        )
        for i in octave_model_IDs
    ]
    r_models = [
        BEASTsdR(
            import_base_path=folder_fmt.format(i), name=model_name_fmt.format(i, "R")
        )
        for i in r_model_IDs
    ]
    return python_models + octave_models + r_models


if __name__ == "__main__":
    # prepare data
    Data = pd.read_csv("CPC18_EstSet.csv")
    stimuli = Data[
        [
            "Ha",
            "pHa",
            "La",
            "LotShapeA",
            "LotNumA",
            "Hb",
            "pHb",
            "Lb",
            "LotShapeB",
            "LotNumB",
            "Amb",
            "Corr",
        ]
    ].values
    actions = Data[["B.1", "B.2", "B.3", "B.4", "B.5"]].values
    obs_dict = {"stimuli": stimuli, "actions": actions}

    # prepare models
    python_model_IDs = [0]
    octave_model_IDs = [1]
    r_model_IDs = [2]
    models = get_models(python_model_IDs, octave_model_IDs, r_model_IDs)

    # prepare tests
    suite = TestSuite(
        [
            MSETest(name="MSE Test", observation=obs_dict),
            MAETest(name="MAE Test", observation=obs_dict),
            CrossEntropyTest(name="Cross Entropy Test", observation=obs_dict, eps=1e-9),
        ],
        name="Batch test suite",
    )

    # judge
    suite.judge(models)

    # TODO: add ability to save testing output results for logging
    # np.savetxt("outputAll.csv", PredictedAll, delimiter=",", header = "B1,B2,B3,B4,B5", fmt='%.4f')

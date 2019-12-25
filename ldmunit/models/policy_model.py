from ldmunit.logging import logger
from ldmunit.utils import negloglike, is_arraylike
from scipy.optimize import minimize
import numpy as np
from collections.abc import Mapping
from gym import spaces
from ldmunit.capabilities import (
    Interactive,
    ProducesPolicy,
    PredictsLogpdf,
    ReturnsNumParams,
)
from ldmunit.continuous import ContinuousSpace
from ldmunit.models import LDMModel
from overrides import overrides


class PolicyModel(LDMModel, Interactive, PredictsLogpdf, ReturnsNumParams):
    """
    PolicyModel provides a model implementation that can be created from agents satisfying :class:`ldmunit.capabilities.ProducesPolicy`
    capability.

    If you already have an agent implementation that can provide a probability distribution over the action space (`eval_policy` method), you
    can create a model of that agent that uses `eval_policy` to make predictions and to fit model parameters (using maximum likelihood) by simply
    deriving from this class. For examples of this, refer to decision making or associative learning model implementations
    provided by `ldmunit`.
    """

    # TODO: can we adapt action and obs spaces according to the Agent (probably not worth it for now)
    def __init__(self, *args, agent, **kwargs):
        assert isinstance(
            agent, ProducesPolicy
        ), "PolicyModel can only accept agents satisfying ProducesPolicy capability"
        super().__init__(*args, **kwargs)
        self.agent = agent
        self.init_paras()
        self.agent.reset()

    @overrides
    def n_params(self):
        return len(self.agent.paras)

    @overrides
    def reset(self):
        self.agent.reset()

    @overrides
    def set_paras(self, paras_dict):
        self.agent.paras = paras_dict

    @overrides
    def get_paras(self):
        return self.agent.paras

    @overrides
    def fit(self, stimuli, rewards, actions):
        self.init_paras()

        def f(x, lens):
            _unpack_array_into_dict(self.agent.paras, x, lens)
            predictions = []
            # TODO: essentially the same logic as InteractiveTesting; refactor?
            self.reset()
            for s, r, a in zip(stimuli, rewards, actions):
                predictions.append(self.predict(s))
                self.update(s, r, a)
            return negloglike(actions, predictions)

        x0, lens = _flatten_dict_into_array(self.agent.paras)
        # TODO: make this modifiable from outside
        opt_res = minimize(
            f, x0, args=(lens,), method="Nelder-Mead", options={"maxiter": 2}
        )
        if not opt_res.success:
            logger().debug(
                f"Fitting on {self.name} has not finished successfully! Cause of termination: {opt_res.message}"
            )

        _unpack_array_into_dict(self.agent.paras, opt_res.x, lens)

        logger().debug(
            f"Agent parameters has been set to the outputs of optimization procedure."
        )

    @overrides
    def predict(self, stimulus):
        policy = self.agent.eval_policy(stimulus)
        return policy.logpdf if hasattr(policy, "logpdf") else policy.logpmf

    def update(self, stimulus, reward, action, done=False):
        """
        Delegate the `update` function to the underlying agent.
        """
        return self.agent.update(stimulus, reward, action, done)

    @overrides
    def act(self, stimulus):
        """
        Delegate the `act` function to the underlying agent.
        """
        return self.agent.act(stimulus)


def _unpack_array_into_dict(dictionary, arr, beg_indices):
    """
    Given an array of scalar values `arr` and a list of begin indices `beg_indices`, assign `i`ith sequence of scalars,
    defined as `arr[beg_indices[i]:beg_indices[i+1]]` to the `i`th key in the dictionary.

    Parameters
    ----------
    dictionary : dict
        Some dictionary. `i`th value of the dictionary is defined as `dictionary[list(dictionary.keys())[i]]`.

    arr : `numpy.ndarray`
        Array containing the values to unpack. `i`th value of the dictionary will be assigned to the `i`th sequence of
        scalars in the array.

    beg_indices : array-like
        Sequence containing the beginning index of every sequence of scalars. `i`th sequence of scalars can be obtained
        as `arr[beg_indices[i]:beg_indices[i+1]]`.
    """
    for i, k in enumerate(dictionary.keys()):
        beg, end = beg_indices[i], beg_indices[i + 1]
        dictionary[k] = arr[beg] if end - beg == 1 else arr[beg:end]


def _flatten_dict_into_array(dictionary, dtype=np.float32):
    """
    Flatten the given dictionary into an array of scalars, and return the beginning index of each sequence of values.

    Parameters
    ----------
    dictionary : dict
        Some dictionary containing scalars or array of scalars as each of its keys.

    dtype : type (optional)
        Data type of the returned array of scalars.

    Returns
    -------
    arr : `numpy.ndarray`
        Consecutive array of scalars containing all the values of the given dictionary.

    beg_indices : `numpy.ndarray`
        Integer array containing the beginning index of each sequence of scalars in `arr`. `i`th value of the dictionary,
        defined as `dictionary[list(dictionary.keys())[i]]` can be obtained as `arr[beg_indices[i]:beg_indices[i+1]]`.
    """
    beg_indices = np.array(
        [0] + [len(v) if is_arraylike(v) else 1 for v in dictionary.values()],
        dtype=np.int32,
    )
    beg_indices = np.cumsum(beg_indices)
    arr = np.empty(beg_indices[-1], dtype=dtype)
    for i, v in enumerate(dictionary.values()):
        beg, end = beg_indices[i], beg_indices[i + 1]
        arr[beg:end] = v
    return arr, beg_indices

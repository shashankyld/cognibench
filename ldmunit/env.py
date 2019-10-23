"""
Some parts of BanditEnv class were inspired by the code at
`<https://github.com/JKCooper2/gym-bandits/blob/master/gym_bandits/bandit.py>`_. We
include a modified version of this code below. The license and copyright notices
of the original bandit.py code (not LDMUnit library) is given below in env.py.
"""
"""
MIT License

Copyright (c) 2016 Jesse Cooper

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import numpy as np
import gym
from gym import spaces
from gym.utils import seeding
from .continuous import ContinuousSpace


class BanditEnv(gym.Env):
    """Bandit environment base to allow agents to interact with the class n-armed bandit
    in different variations

    BanditEnv will initialize a :class:`gym.Env` instance in which rewards (1 or 0) will be 
    randomly rewarded towards the agents with the probability set.

    Parameters
    ----------
    p_dist : list
        A list of probabilities of the likelihood that a particular bandit will pay out.
    info : str
        Info about the environment that the agents is not supposed to know. For instance,
        info can releal the index of the optimal arm, or the value of prior parameter.
        Can be useful to evaluate the agent's perfomance

    Attributes
    ----------
    p_dist : list
        A list of probabilities of the likelihood that a particular bandit will pay out.
    info : str
        Info about the environment that the agents is not supposed to know. For instance,
        info can releal the index of the optimal arm, or the value of prior parameter.
        Can be useful to evaluate the agent's perfomance.
    n_bandits : int
        Number of bandits set by p_dist.
    action_space : :class:`gym.spaces.Discrete`
        Environment only understand discrete action set in this space (set by length of p_dist).
    observation_space : :class:`gym.spaces.Discrete`
        There is no observation/stimulus/cue in bandit environment.
    """

    def __init__(self, p_dist, info={}):
        if min(p_dist) < 0 or max(p_dist) > 1:
            raise ValueError("All probabilities must be between 0 and 1")

        self.p_dist = p_dist
        self.info = info
        self.n_bandits = len(p_dist)
        self.action_space = spaces.Discrete(self.n_bandits)
        self.observation_space = spaces.Discrete(1)
        self.seed()

    def seed(self, seed=None):
        """Set the random_state for the environment if given.

        Parameters
        ----------
        seed : int
            Seed for the random_state
        """
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, action):
        """Environment reacts to the agent.

        Parameters
        ----------
        action : int
            Action taken by the agent

        Returns
        -------
        observation : int
            No observation for n-bandit test.
        reward : int
            1 or 0 generated by the p_dist.
        done : bool
            Whether the environment has been exceeded.
        info : str
            Information about the environment.
        """
        assert self.action_space.contains(
            action
        ), "Action does not fit in the environment's action_space"
        reward = 0
        done = False
        observation = 0
        info = self.info

        if self.np_random.uniform() < self.p_dist[action]:
            reward = 1

        return observation, reward, done, info

    def reset(self):
        """Reset the n-bandit env.

        Since there is no memory preserved by the environment no operation on the env.
        """
        return self.observation_space.sample()

    def render(self, mode="human", close=False):
        """
        Not implemented
        """
        pass


class BanditAssociateEnv(gym.Env):
    """Environment base to allow agents to learn from stimulus occuring at different
    probabilities.

    BanditEnv will initialize a :class:`gym.Env` instance in which rewards (1 or 0) will be 
    randomly rewarded towards pre-set stimuli. The occurance of the stimulus 
    will be determined by the `p_stimuli`

    Parameters
    ----------
    stimuli : list
        A list of stimulus in the same :class:`gym.spaces.MultiBinary` space.
    p_stimuli : list
        A list of probabilities that a stimulus will occur.
    p_reward : list
        A list of probabilities of the likelihood that a particular stimuli will pay out.
    info : str
        Info about the environment that the agents is not supposed to know. For instance,
        info can releal the index of the optimal arm, or the value of prior parameter.
        Can be useful to evaluate the agent's perfomance.

    Attributes
    ----------
    p_stimuli : list
        A list of probabilities that a stimulus will occur.
    p_reward : list
        A list of probabilities of the likelihood that a particular stimuli will pay out.
    info : str
        Info about the environment that the agents is not supposed to know. For instance,
        info can releal the index of the optimal arm, or the value of prior parameter.
        Can be useful to evaluate the agent's perfomance
    action_space : :class:`ldmunit.continuous.ContinuousSpace`
        Environment only understand discrete action set in this space (set by length of p_dist).
    observation_space : :class:`gym.spaces.MultiBinary`
        The multi-binary space set by the stimuli
         
    """

    def __init__(self, stimuli, p_stimuli, p_reward, info={}):
        if min(p_stimuli) < 0 or max(p_stimuli) > 1 or sum(p_stimuli) != 1:
            raise ValueError("All probabilities must be between 0 and 1")
        if min(p_reward) < 0 or max(p_reward) > 1:
            raise ValueError("All probabilities must be between 0 and 1")
        assert (
            len(set(map(len, (p_stimuli, stimuli, p_reward)))) == 1
        ), "Stimuli and Probability list must be of equal length"
        self._n = len(stimuli[0])
        self.observation_space = spaces.MultiBinary(self._n)
        self.action_space = ContinuousSpace()
        for s in stimuli:
            assert self.observation_space.contains(
                s
            ), "Stimuli must be in the same MultiBinary space"

        self.stimuli = stimuli
        self.p_stimuli = p_stimuli
        self.p_reward = p_reward
        self.info = info

        self.seed()

    def seed(self, seed=None):
        """Set the random_state for the environment if given.

        Parameters
        ----------
        seed : int
            Seed for the random_state
        """
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, action):
        """Environment reacts to the agent.

        Parameters
        ----------
        action : int
            Action taken by the agent

        Returns
        -------
        observation : :class:`numpy.ndarray`
            stimulus from the pre-set list
        reward : int
            1 or 0 generated by the p_dist.
        done : bool
            Whether the environment has been exceeded.
        info : str
            Information about the environment.
        """
        assert self.action_space.contains(
            action
        ), "Action does not fit in the environment's action_space"

        obs_idx = self.np_random.choice(
            range(len(self.stimuli)), p=self.p_stimuli, replace=True
        )
        reward = 0
        done = False
        observation = self.stimuli[obs_idx]
        info = self.info

        if self.np_random.uniform() < self.p_reward[obs_idx]:
            reward = 1

        return observation, reward, done, info

    def reset(self):
        """Reset the n-bandit env.

        Since there is no memory perserved by the environment. No operation on 
        the env.

        Returns
        -------
        observation : :class:`numpy.ndarray`
            One of the stimulus from the pre-set list
        """
        obs_idx = self.np_random.choice(
            range(len(self.stimuli)), p=self.p_stimuli, replace=True
        )
        observation = self.stimuli[obs_idx]
        return observation

    def render(self, mode="human", close=False):
        """
        Not implemented
        """
        pass

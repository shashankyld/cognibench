import sciunit
import numpy as np
import gym
from gym import spaces
from scipy import stats
from .rw_norm import RwNormModel

class LSSPDModel(RwNormModel):

    def __init__(self, n_obs=None, paras=None, hidden_state=None, name=None, **params):
        return super().__init__(n_obs=n_obs, paras=paras, hidden_state=hidden_state, name=name, **params)

    def reset(self):
        w0 = self.paras['w0'] if 'w0' in self.paras else 0
        alpha = self.paras['alpha'] if 'alpha' in self.paras else 0

        w0 = np.array(w0) if isinstance(w0, list) else np.full(self.n_obs, w0)
        alpha = np.array(alpha) if isinstance(alpha, list) else np.full(self.n_obs, alpha)

        hidden_state = {'w'    : w0,
                        'alpha': alpha}

        self.hidden_state = hidden_state

    def observation(self, stimulus, paras=None):
        if not paras:
            paras = self.paras
        assert isinstance(self.observation_space, spaces.MultiBinary), "observation space must be set first"
        assert self.observation_space.contains(stimulus)

        b0 = paras['b0'] # intercept
        b1 = paras['b1'] # slope
        sd_pred = paras['sigma']
        mix_coef = paras['mix_coef'] # proportion of the weights signal in the mixture of weight and associability signals
        
        w_curr = self.hidden_state['w']
        alpha  = self.hidden_state['alpha']

        # Predict response
        mu_pred = b0 + b1 * np.dot(stimulus, (mix_coef * w_curr + (1 - mix_coef) * alpha))

        rv = stats.norm(loc=mu_pred, scale=sd_pred)
        if self.seed:
            rv.random_state = self.seed

        return rv
        
    def update(self, stimulus, reward, action, done, paras=None):
        if not paras:
            paras = self.paras
        assert self.action_space.contains(action)
        assert self.observation_space.contains(stimulus)

        eta   = paras['eta'] # Proportion of pred. error. in the updated associability value
        kappa = paras['kappa'] # Fixed learning rate for the cue weight update
        
        w_curr = self.hidden_state['w']
        alpha  = self.hidden_state['alpha']

        rhat = self._predict_reward(stimulus, paras=paras)


        if not done:
            delta = reward - rhat

            w_curr += kappa * delta * alpha * stimulus # alpha, stimulus size: (n_obs,)

            # if stimulus[i] = 1
            # alpha[i] = eta * abs(pred_err) + (1 - eta) * alpha[i]
            # or
            # alpha[i] -= eta * alpha[i]
            # alpha[i] += eta * abs(pred_err)
            alpha -= eta * np.multiply(alpha, stimulus)
            alpha += eta * abs(delta) * stimulus
            np.clip(alpha, a_min=0, a_max=1, out=alpha) # Enforce upper bound on alpha

            self.hidden_state['w'] = w_curr
            self.hidden_state['alpha'] = alpha

        return w_curr, alpha
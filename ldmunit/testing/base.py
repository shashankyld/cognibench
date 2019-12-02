import os
import collections
import pickle
import numpy as np
from sciunit import Test
from sciunit.errors import Error
from ldmunit.models import LDMModel
from ldmunit.capabilities import Interactive, BatchTrainable, MultiSubjectModel
from ldmunit.models.utils import single_from_multi_obj, reverse_single_from_multi_obj


class LDMTest(Test):
    score_type = None

    def __init__(
        self,
        *args,
        score_type=None,
        multi_subject=False,
        score_aggr_fn=np.mean,
        persist_path=None,
        logging=1,
        fn_kwargs_for_score=None,
        **kwargs,
    ):
        self.multi_subject = multi_subject
        self.score_aggr_fn = score_aggr_fn
        self.persist_path = persist_path
        self.logging = logging
        self.fn_kwargs_for_score = fn_kwargs_for_score

        if score_type is not None:
            self.score_type = score_type
            try:
                score_capabilities = self.score_type.required_capabilities
                self.required_capabilities = (
                    LDMTest.required_capabilities + score_capabilities
                )
            except AttributeError:
                pass
        super().__init__(*args, **kwargs)

    def check_capabilities(self, model, **kwargs):
        if not isinstance(model, LDMModel):
            raise Error(f"Model {model} is not an instance of LDMModel")
        super().check_capabilities(model, **kwargs)

    def _get_observations(self):
        if self.multi_subject:
            return self.observation["list"]
        else:
            return self.observation

    def generate_prediction(self, model):
        observations = self._get_observations()
        if self.multi_subject:
            assert isinstance(
                model, MultiSubjectModel
            ), "Multi subject tests can only accept multi subject models"
            n_subj = len(observations)
            predictions = []
            score_kwargs = []
            for subj_idx in range(n_subj):
                single_subj_adapter = single_from_multi_obj(model, subj_idx)
                pred_single = self.predict_single(
                    single_subj_adapter, observations[subj_idx]
                )
                predictions.append(pred_single)
                score_kwargs.append(
                    self.get_kwargs_for_compute_score(
                        model, observations[subj_idx], pred_single
                    )
                )
                model = reverse_single_from_multi_obj(single_subj_adapter)
        else:
            predictions = self.predict_single(model, observations)
            score_kwargs = self.get_kwargs_for_compute_score(
                model, observations, predictions
            )

        self.score_kwargs = score_kwargs
        return predictions

    def get_kwargs_for_compute_score(self, model, observations, predictions):
        if self.fn_kwargs_for_score is not None:
            return self.fn_kwargs_for_score(model, observations, predictions)
        else:
            return dict()

    def compute_score(self, _, predictions, **kwargs):
        observations = self._get_observations()
        if self.multi_subject:
            n_subj = len(observations)
            scores = []
            for subj_idx in range(n_subj):
                scores.append(
                    self.compute_score_single(
                        observations[subj_idx],
                        predictions[subj_idx],
                        **self.score_kwargs[subj_idx],
                        **kwargs,
                    ).score
                )
            score = self.score_aggr_fn(scores)
        else:
            score = self.compute_score_single(
                observations, predictions, **self.score_kwargs, **kwargs
            ).score
        return self.score_type(score)

    def predict_single(self, model, observations, **kwargs):
        raise NotImplementedError(
            "predict_single must be implemented by concrete Test classes"
        )

    def compute_score_single(self, observations, predictions, **kwargs):
        raise NotImplementedError(
            "compute_score_single must be implemented by concrete Test classes"
        )

    def bind_score(self, score, model, observation, prediction):
        if self.logging > 0:
            print()
        if self.persist_path is None:
            return

        folderpath = os.path.join(self.persist_path, model.name)
        os.makedirs(folderpath, exist_ok=True)
        score_filepath = os.path.join(folderpath, "score")
        pred_filepath = os.path.join(folderpath, "predictions")
        model_filepath = os.path.join(folderpath, "model")
        self._persist_score(score_filepath, score)
        self._persist_predictions(pred_filepath, prediction)
        self._persist_model(model_filepath, model)
        if self.logging > 0:
            print("Data saving is complete")

    def _persist_score(self, path, score):
        np.save(path, np.asarray(score.score))
        if self.logging > 1:
            print(f"Score is saved in {path}")

    def _persist_predictions(self, path, predictions):
        np.save(path, np.asarray(predictions))
        if self.logging > 1:
            print(f"Predictions are saved in {path}")

    def _persist_model(self, path, model):
        try:
            model.save(path)
            if self.logging > 1:
                print(f"Model is saved in {path}")
        except AttributeError:
            modelname = model.name
            if self.logging > 1:
                print(
                    f"Model {modelname} does not implement save method, saving unsuccessful"
                )


class InteractiveTest(LDMTest):
    """
    TODO: update the comment, it is deprecated.
    Perform interactive tests by feeding the input samples (stimuli) one at a
    time. This class is not intended to be used directly since it does not
    specify how the score should be computed. In order to create concrete
    interactive tests, create a subclass and specify how the score should be
    computed.

    See Also
    --------
    :class:`NLLTest`, :class:`AICTest`, :class:`BICTest` for examples of concrete interactive test classes
    """

    required_capabilities = (Interactive,)

    def __init__(self, *args, **kwargs):
        """
        Other Parameters
        ----------------
        **kwargs : any type
            All the keyword arguments are passed to `__init__` method of :class:`sciunit.tests.Test`.
            `observation` dictionary must contain 'stimuli', 'rewards' and 'actions' keys.
            Value for each these keys must be a list of list (or any other iterable) where
            outer list is over subjects and inner list is over samples.

        See Also
        --------
        :py:meth:`InteractiveTest.generate_prediction`
        """
        super().__init__(*args, **kwargs)

    def predict_single(self, model, observations, **kwargs):
        """
        Generate predictions from a multi-subject model one at a time.

        Parameters
        ----------
        multimodel : :class:`ldmunit.models.LDMModel` and :class:`ldmunit.capabilities.Interactive`
            Multi-subject model

        Returns
        -------
        list of list
            Predictions
        """
        stimuli = observations["stimuli"]
        rewards = observations["rewards"]
        actions = observations["actions"]

        predictions = []
        model.reset()
        for s, r, a in zip(stimuli, rewards, actions):
            predictions.append(model.predict(s))
            model.update(s, r, a, False)
        return predictions

    def compute_score_single(self, observations, predictions, **kwargs):
        return self.score_type.compute(observations["actions"], predictions, **kwargs)


class BatchTest(LDMTest):
    def __init__(self, *args, **kwargs):
        """
        TODO: update the comment, it is deprecated.
        Perform batch tests by predicting the outcome for each input sample without
        doing any model update. This class is not intended to be used directly since
        it does not specify how the score should be computed. In order to create
        concrete batch tests, create a subclass and specify how the score
        should be computed.

        Other Parameters
        ----------------
        **kwargs : any type
            All the keyword arguments are passed to `__init__` method of :class:`sciunit.tests.Test`.
            `observation` dictionary must contain 'stimuli', and 'actions' keys.
            Value for each these keys must be a list of 'stimuli' resp. 'action'.

        See Also
        --------
        :py:meth:`BatchTest.generate_prediction`
        """
        super().__init__(*args, **kwargs)

    def predict_single(self, model, observations, **kwargs):
        """
        Generate predictions from a given model

        Parameters
        ----------
        model : :class:`ldmunit.models.LDMModel`
            Model to test

        Returns
        -------
        list
            Predictions
        """
        return model.predict(observations["stimuli"])

    def compute_score_single(self, observations, predictions, **kwargs):
        return self.score_type.compute(observations["actions"], predictions, **kwargs)


class BatchTrainAndTest(LDMTest):
    required_capabilities = (BatchTrainable,)

    def __init__(
        self,
        *args,
        train_percentage=0.75,
        seed=None,
        train_indices=None,
        test_indices=None,
        **kwargs,
    ):
        """
        If train_indices is given, it is used; else, a random train/test split is used.
        """
        assert (
            train_percentage > 0 and train_percentage < 1
        ), "train_percentage must be in range (0, 1)"
        super().__init__(*args, **kwargs)
        if train_indices is None:
            assert test_indices is None
            n_obs = len(self.observation["stimuli"])
            indices = np.arange(n_obs, dtype=np.int64)
            np.random.RandomState(seed).shuffle(indices)
            n_train = round(n_obs * train_percentage)
            self.train_indices = indices[:n_train]
            self.test_indices = indices[n_train:]
        else:
            assert test_indices is not None
            self.train_indices = train_indices
            self.test_indices = test_indices

    def predict_single(self, model, observations, **kwargs):
        x_train = observations["stimuli"][self.train_indices]
        y_train = observations["actions"][self.train_indices]
        model.fit(x_train, y_train)

        x_test = observations["stimuli"][self.test_indices]
        predictions = np.asarray(model.predict(x_test))

        return predictions

    def compute_score_single(self, observations, predictions, **kwargs):
        actions = observations["actions"][self.test_indices]
        return self.score_type.compute(actions, predictions, **kwargs)

    def persist_predictions(self, path, predictions):
        indices_path = f"{path}_indices"
        np.save(indices_path, self.test_indices)
        if self.logging > 1:
            print(f"Indices are saved in {indices_path}")
        super().persist_predictions(path, predictions)

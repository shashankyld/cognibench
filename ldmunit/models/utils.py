import gym
import types
from functools import partial
import sciunit
import numpy as np
from ldmunit.capabilities import Interactive, MultiSubjectModel


def multi_from_single_cls(method_names, single_cls):
    """
    Create a multi-subject model from a single-subject model.

    Parameters
    ----------
    method_names : list of str
        List of methods that will transform to multi-subject variants.

    single_cls : :class:`ldmunit.model.LDMModel`
        A single-subject model class.

    Returns
    -------
    out_cls : :class:`ldmunit.model.LDMModel`
        A multi-subject model class. Each passed method now takes a subject index as their first argument.
    """
    multi_cls_name = "Multi" + single_cls.__name__
    return MultiMeta(
        multi_cls_name,
        (single_cls,),
        {
            "name": single_cls.name,
            "__doc__": single_cls.__doc__,
            "_method_names": method_names,
        },
    )


multi_from_single_interactive = partial(
    multi_from_single_cls, ("act", "fit", "predict", "reset", "update")
)
multi_from_single_interactive_parametric = partial(
    multi_from_single_cls, ("act", "fit", "predict", "reset", "update", "n_params")
)


# PRIVATE DETAIL FUNCTIONS; use at your own risk


class MultiMeta(type):
    """
    MultiMetaInteractive is a metaclass for creating multi-subject models from
    single-subject ones.

    Each input method to this metaclass takes an additional subject
    index as their first argument afterwards. This index is used to select the individual
    single-subject model to use. In this regard, the returned class is semantically
    similar to a list of single-subject models while also satisfying model class requirements.

    This metaclass is not intended to be used directly. Users should use
    multi_from_single_cls or its derivatives for automatically generating multi-subject models
    from single-subject ones.

    See Also
    --------
    multi_from_single_cls, multi_from_single_interactive
    """

    def __new__(cls, name, bases, dct):
        single_cls = bases[0]
        base_classes = single_cls.__bases__ + (MultiSubjectModel,)
        out_cls = super().__new__(cls, name, base_classes, dct)

        def multi_init(self, param_list, *args, **kwargs):
            self.subject_models = []
            for param_dict in param_list:
                self.subject_models.append(single_cls(*args, **param_dict, **kwargs))

            def new_fn(idx, *args, fn_name, **kwargs):
                return getattr(self.subject_models[idx], fn_name)(*args, **kwargs)

            for fn_name in dct["_method_names"]:
                setattr(out_cls, fn_name, partial(new_fn, fn_name=fn_name))

        def fit_jointly(self, *args, **kwargs):
            """
            Default implementation simply fits each subject model separately. In case you need more complex behaviour,
            such as hierarchical joint fitting of the subject models, you can

            1. define your separate multi-subject model, or
            2. subclass the output of this metaclass and override `fit_jointly` to perform the
            desired fitting procedure.

            Parameters
            ----------
            args : iterable
                Each positional argument to this function must be an iterable that contains the subject-specific
                fitting arguments.
            kwargs : dict
                Each keyword argument to this function must be an iterable that contains the subject-specific fitting
                keyword arguments.
            """
            for i, model in enumerate(self.subject_models):
                curr_args = []
                curr_kwargs = dict()
                for arg in args:
                    curr_args.append(arg[i])
                for k, v in kwargs.items():
                    curr_kwargs[k] = v[i]
                model.fit(*curr_args, **curr_kwargs)

        out_cls.__init__ = multi_init
        out_cls.fit_jointly = fit_jointly
        out_cls.multi_subject_methods = dct["_method_names"]

        return out_cls


def single_from_multi_obj(model, subj_idx):
    """
    Temporarily convert a multi-subject model created by multi_from_single_cls or its derivatives to a single-subject
    for the given subject index. The model returned by this function behaves as a single-subject model where the subject
    is given by `subj_idx`. The multi-subject variants of the replaced methods are stored with multi suffix to be restored
    later.
    """
    assert isinstance(model, MultiSubjectModel)

    def make_new_fn(old_fn):
        def new_fn(self, *args, **kwargs):
            return old_fn(subj_idx, *args, **kwargs)

        return new_fn

    for fn_name in model.multi_subject_methods:
        old_fn = getattr(model, fn_name)
        new_fn = make_new_fn(old_fn)
        setattr(model, f"{fn_name}_multi", old_fn)
        setattr(model, fn_name, new_fn.__get__(model))
    return model


def reverse_single_from_multi_obj(model):
    """
    Reverse a single from multi object conversion performed by `single_from_multi_obj`.
    """
    for fn_name in model.multi_subject_methods:
        multi_name = f"{fn_name}_multi"
        old_fn = getattr(model, multi_name)
        setattr(model, fn_name, old_fn)
        delattr(model, multi_name)
    return model

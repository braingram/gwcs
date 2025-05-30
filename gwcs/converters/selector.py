# Licensed under a 3-clause BSD style license - see LICENSE.rst

from collections import OrderedDict

import numpy as np
from asdf.tags.core.ndarray import NDArrayType
from asdf_astropy.converters.transform.core import TransformConverterBase
from astropy.modeling import models
from astropy.modeling.core import Model

__all__ = ["LabelMapperConverter", "RegionsSelectorConverter"]


class LabelMapperConverter(TransformConverterBase):
    tags = ("tag:stsci.edu:gwcs/label_mapper-*",)
    types = (
        "gwcs.selector.LabelMapperArray",
        "gwcs.selector.LabelMapperDict",
        "gwcs.selector.LabelMapperRange",
        "gwcs.selector.LabelMapper",
    )

    def from_yaml_tree_transform(self, node, tag, ctx):
        from gwcs.selector import (
            LabelMapper,
            LabelMapperArray,
            LabelMapperDict,
            LabelMapperRange,
        )

        inputs_mapping = node.get("inputs_mapping", None)
        if inputs_mapping is not None and not isinstance(
            inputs_mapping, models.Mapping
        ):
            msg = (
                "inputs_mapping must be an instanceof astropy.modeling.models.Mapping."
            )
            raise TypeError(msg)
        mapper = node["mapper"]
        atol = node.get("atol", 1e-8)
        no_label = node.get("no_label", np.nan)

        if isinstance(mapper, NDArrayType):
            if mapper.ndim != 2:
                msg = "GWCS currently only supports 2D masks."
                raise NotImplementedError(msg)
            return LabelMapperArray(mapper, inputs_mapping)
        if isinstance(mapper, Model):
            inputs = node.get("inputs")
            return LabelMapper(
                inputs, mapper, inputs_mapping=inputs_mapping, no_label=no_label
            )
        inputs = node.get("inputs", None)
        if inputs is not None:
            inputs = tuple(inputs)
        labels = mapper.get("labels")
        transforms = mapper.get("models")
        if np.iterable(labels[0]):
            labels = [tuple(label) for label in labels]
            dict_mapper = dict(zip(labels, transforms, strict=False))
            return LabelMapperRange(inputs, dict_mapper, inputs_mapping)
        dict_mapper = dict(zip(labels, transforms, strict=False))
        return LabelMapperDict(inputs, dict_mapper, inputs_mapping, atol=atol)

    def to_yaml_tree_transform(self, model, tag, ctx):
        from gwcs.selector import (
            LabelMapper,
            LabelMapperArray,
            LabelMapperDict,
            LabelMapperRange,
        )

        node = OrderedDict()
        node["no_label"] = model.no_label
        if model.inputs_mapping is not None:
            node["inputs_mapping"] = model.inputs_mapping

        if isinstance(model, LabelMapperArray):
            node["mapper"] = model.mapper
        elif isinstance(model, LabelMapper):
            node["mapper"] = model.mapper
            node["inputs"] = list(model.inputs)
        elif isinstance(model, (LabelMapperDict, LabelMapperRange)):  # noqa: UP038
            if hasattr(model, "atol"):
                node["atol"] = model.atol
            mapper = OrderedDict()
            labels = list(model.mapper)

            transforms = [model.mapper[k] for k in labels]
            if np.iterable(labels[0]):
                labels = [list(label) for label in labels]
            mapper["labels"] = labels
            mapper["models"] = transforms
            node["mapper"] = mapper
            node["inputs"] = list(model.inputs)
        else:
            msg = f"Unrecognized type of LabelMapper - {model}"
            raise TypeError(msg)

        return node


class RegionsSelectorConverter(TransformConverterBase):
    tags = ("tag:stsci.edu:gwcs/regions_selector-*",)
    types = ("gwcs.selector.RegionsSelector",)

    def from_yaml_tree_transform(self, node, tag, ctx):
        from gwcs.selector import RegionsSelector

        inputs = node["inputs"]
        outputs = node["outputs"]
        label_mapper = node["label_mapper"]
        undefined_transform_value = node["undefined_transform_value"]
        sel = node["selector"]
        sel = dict(zip(sel["labels"], sel["transforms"], strict=False))
        return RegionsSelector(
            inputs, outputs, sel, label_mapper, undefined_transform_value
        )

    def to_yaml_tree_transform(self, model, tag, ctx):
        selector = OrderedDict()
        node = OrderedDict()
        labels = list(model.selector)
        values = [model.selector[label] for label in labels]
        selector["labels"] = labels
        selector["transforms"] = values
        node["inputs"] = list(model.inputs)
        node["outputs"] = list(model.outputs)
        node["selector"] = selector
        node["label_mapper"] = model.label_mapper
        node["undefined_transform_value"] = model.undefined_transform_value
        return node

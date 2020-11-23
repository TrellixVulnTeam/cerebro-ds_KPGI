# coding=utf-8
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import numpy as np

import json
# TODO
# 1. Current serializing logic
    # serialized string -> byte string
    # np.array(np.array(image_count).concatenate(weights_np_array)).tostring()
    # Proposed logic
    # image_count can be a separate value
    # weights -> np.array(weights).tostring()
    # combine these 2 into one string by a random splitter
    # serialized string -> imagecount_splitter_weights
# 2. combine the serialize_state_with_nd_weights and serialize_state_with_1d_weights
    # into one function called serialize_state. This function can infer the shape
    # of the model weights and then flatten if they are nd weights.
# 3. Same as 2 for deserialize


"""
workflow
1. Set initial weights in madlib keras fit function.
2. Serialize these initial model weights as a byte string and pass it to keras step
3. Deserialize the state passed from the previous step into a list of nd weights
that will be passed on to model.set_weights()
4. At the end of each buffer in fit transition, serialize the image count and
the model weights into a bytestring that will be passed on to the fit merge function.
5. In fit merge, deserialize the state as image and 1d np arrays. Do some averaging
operations and serialize them again into a state which contains the image
and the 1d state. same for fit final
6. Return the final state from fit final to fit which will then be deserialized
as 1d weights to be passed on to the evaluate function
"""
def get_serialized_1d_weights_from_state(state):
    """
    Output of this function is used to deserialize the output of each iteration
    of madlib keras step UDA.

    :param state: bytestring serialized model state containing image count
    and weights
    :return: model weights serialized as bytestring
    """
    _ , weights = deserialize_as_image_1d_weights(state)
    return weights.tostring()

def serialize_state_with_nd_weights(image_count, model_weights):
    """
    This function is called when the output of keras.get_weights() (list of nd
    np arrays) has to be converted into a serialized model state.

    :param image_count: float value
    :param model_weights: a list of numpy arrays, what you get from
        keras.get_weights()
    :return: Image count and model weights serialized into a bytestring format

    """
    if model_weights is None:
        return None
    flattened_weights = [w.flatten() for w in model_weights]
    state = [np.array([image_count])] + flattened_weights
    state = np.concatenate(state)
    return np.float32(state).tostring()


def serialize_state_with_1d_weights(image_count, model_weights):
    """
    This function is called when the weights are to be passed to the keras fit
    merge and final functions.

    :param image_count: float value
    :param model_weights: a single flattened numpy array containing all of the
        weights
    :return: Image count and model weights serialized into a bytestring format

    """
    if model_weights is None:
        return None
    merge_state = np.array([image_count])
    merge_state = np.concatenate((merge_state, model_weights))
    merge_state = np.float32(merge_state)
    return merge_state.tostring()


def deserialize_as_image_1d_weights(state):
    """
    This function is called when the model state needs to be deserialized in
    the keras fit merge and final functions.

    :param state: the stringified (serialized) state containing image_count and
            model_weights
    :return:
        image_count: total buffer counts processed
        model_weights: a single flattened numpy array containing all of the
        weights
    """
    if not state:
        return None
    state = np.fromstring(state, dtype=np.float32)
    return float(state[0]), state[1:]


def serialize_nd_weights(model_weights):
    """
    This function is called for passing the initial model weights from the keras
    fit function to the keras fit transition function.
    :param model_weights: a list of numpy arrays, what you get from
        keras.get_weights()
    :return: Model weights serialized into a bytestring format
    """
    if model_weights is None:
        return None
    flattened_weights = [w.flatten() for w in model_weights]
    flattened_weights = np.concatenate(flattened_weights)
    return np.float32(flattened_weights).tostring()


def deserialize_as_nd_weights(model_weights_serialized, model_shapes):
    """
    The output of this function is used to set keras model weights using the
    function model.set_weights()
    :param model_weights_serialized: bytestring containing model weights
    :param model_shapes: list containing the shapes of each layer.
    :return: list of nd numpy arrays containing all of the
        weights
    """
    if not model_weights_serialized or not model_shapes:
        return None

    i, j, model_weights = 0, 0, []
    model_weights_serialized = np.fromstring(model_weights_serialized, dtype=np.float32)

    total_model_shape = \
        sum([reduce(lambda x, y: x * y, ls) for ls in model_shapes])
    total_weights_shape = model_weights_serialized.size
    assert(total_model_shape == total_weights_shape,
            "Number of elements in model weights({0}) doesn't match model({1})."\
                .format(total_weights_shape, total_model_shape))
    while j < len(model_shapes):
        next_pointer = i + reduce(lambda x, y: x * y, model_shapes[j])
        weight_arr_portion = model_weights_serialized[i:next_pointer]
        model_weights.append(np.array(weight_arr_portion).reshape(model_shapes[j]))
        i, j = next_pointer, j + 1
    return model_weights


def _get_layers(model_arch):
    d = json.loads(model_arch)
    config = d['config']
    if type(config) == list:
        return config  # In keras 2.1.x, all models are sequential
    elif type(config) == dict and 'layers' in config:
        layers = config['layers']
        if type(layers) == list:
            return config['layers']  # In keras 2.x, only sequential models are supported
    raise Exception("Unable to read model architecture JSON.")

def get_input_shape(model_arch):
    arch_layers = _get_layers(model_arch)
    if 'batch_input_shape' in arch_layers[0]['config']:
        return arch_layers[0]['config']['batch_input_shape'][1:]
    raise Exception('Unable to get input shape from model architecture.')

def get_num_classes(model_arch):
    """
     We assume that the last dense layer in the model architecture contains the num_classes (units)
     An example can be:
     ```
     ...
     model.add(Flatten())
     model.add(Dense(512))
     model.add(Activation('relu'))
     model.add(Dropout(0.5))
     model.add(Dense(num_classes))
     model.add(Activation('softmax'))
     ```
     where activation can be after the dense layer.
    :param model_arch:
    :return:
    """
    arch_layers = _get_layers(model_arch)
    i = len(arch_layers) - 1
    while i >= 0:
        if 'units' in arch_layers[i]['config']:
            return arch_layers[i]['config']['units']
        i -= 1
    raise Exception('Unable to get number of classes from model architecture.')

def get_model_arch_layers_str(model_arch):
    arch_layers = _get_layers(model_arch)
    layers = "Model arch layers:\n"
    first = True
    for layer in arch_layers:
        if first:
            first = False
        else:
            layers += "   |\n"
            layers += "   V\n"
        class_name = layer['class_name']
        config = layer['config']
        if class_name == 'Dense':
            layers += "{1}[{2}]\n".format(class_name, config['units'])
        else:
            layers += "{1}\n".format(class_name)
    return layers
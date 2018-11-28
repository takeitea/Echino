"""
Copyright 2017-2018 Fizyr (https://fizyr.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import keras
from . import backend
from keras import backend as k
import tensorflow as tf
import functools
from keras.layers import Lambda


def focal(alpha=0.25, gamma=2.0, center_alpha=0.03, num_calsses=9):
    """ Create a functor for computing the focal loss.

    Args
        alpha: Scale the focal weight with alpha.
        gamma: Take the power of the focal weight with gamma.

    Returns
        A functor that computes the focal loss using the alpha and gamma.
    """
    center = k.zeros([num_calsses,])

    @functools.wraps(_focal)
    def center_loss(y_true, y_pred):
        return _focal(y_true, y_pred, alpha, gamma, center_alpha, num_calsses, center)

    return center_loss


def _focal(y_true, y_pred, alpha, gamma, center_alpha, num_classes, center):
    """ Compute the focal loss given the target tensor and the predicted tensor.

    As defined in https://arxiv.org/abs/1708.02002

    Args
        y_true: Tensor of target data from the generator with shape (B, N, num_classes).
        y_pred: Tensor of predicted data from the network with shape (B, N, num_classes).

    Returns
        The focal loss of y_pred w.r.t. y_true.
    """
    labels = y_true[:, :, :-1]
    anchor_state = y_true[:, :, -1]  # -1 for ignore, 0 for background, 1 for object
    # split =Lambda( lambda x: tf.split(x,num_or_size_splits=2,axis=1) )(y_pred)
    # split=tf.split(y_true,2)(y_pred)
    classification = keras.layers.Activation('sigmoid', name="classification_loss")(y_pred)

    # classification feature
    feature = y_pred

    # filter out "ignore" anchors
    indices = backend.where(keras.backend.not_equal(anchor_state, -1))
    labels = backend.gather_nd(labels, indices)

    classification = backend.gather_nd(classification, indices)

    feature = backend.gather_nd(feature, indices)

    # compute the focal loss
    alpha_factor = keras.backend.ones_like(labels) * alpha
    alpha_factor = backend.where(keras.backend.equal(labels, 1), alpha_factor, 1 - alpha_factor)
    focal_weight = backend.where(keras.backend.equal(labels, 1), 1 - classification, classification)
    focal_weight = alpha_factor * focal_weight ** gamma

    cls_loss = focal_weight * keras.backend.binary_crossentropy(labels, classification)
    # compute the normalizer: the number of positive anchors
    normalizer = backend.where(keras.backend.equal(anchor_state, 1))
    normalizer = keras.backend.cast(keras.backend.shape(normalizer)[0], keras.backend.floatx())
    normalizer = keras.backend.maximum(1.0, normalizer)

    # compute the center loss
    # labels = k.reshape(labels, [-1, 9])
    labels = tf.to_int32(labels)
    centers_batch = tf.gather(center, labels)

    # diff = (1 - center_alpha) * (centers_batch - feature)
    # center = tf.scatter_sub(center, labels, diff)
    # loss = tf.reduce_mean(k.square(tf.to_float(labels) - centers_batch))
    # loss += keras.backend.sum(cls_loss)
    diff =  centers_batch - feature
    # center = tf.scatter_sub(center, labels, diff)
    loss = tf.reduce_mean(k.square(diff))*center_alpha
    loss += keras.backend.sum(cls_loss)
    return keras.backend.sum(loss) / normalizer


def smooth_l1(sigma=3.0):
    """ Create a smooth L1 loss functor.

    Args
        sigma: This argument defines the point where the loss changes from L2 to L1.

    Returns
        A functor for computing the smooth L1 loss given target data and predicted data.
    """
    sigma_squared = sigma ** 2

    def _smooth_l1(y_true, y_pred):
        """ Compute the smooth L1 loss of y_pred w.r.t. y_true.

        Args
            y_true: Tensor from the generator of shape (B, N, 5). The last value for each box is the state of the anchor (ignore, negative, positive).
            y_pred: Tensor from the network of shape (B, N, 4).

        Returns
            The smooth L1 loss of y_pred w.r.t. y_true.
        """
        # separate target and state
        regression = y_pred
        regression_target = y_true[:, :, :-1]
        anchor_state = y_true[:, :, -1]

        # filter out "ignore" anchors
        indices = backend.where(keras.backend.equal(anchor_state, 1))
        regression = backend.gather_nd(regression, indices)
        regression_target = backend.gather_nd(regression_target, indices)

        # compute smooth L1 loss
        # f(x) = 0.5 * (sigma * x)^2          if |x| < 1 / sigma / sigma
        #        |x| - 0.5 / sigma / sigma    otherwise
        regression_diff = regression - regression_target
        regression_diff = keras.backend.abs(regression_diff)
        regression_loss = backend.where(
            keras.backend.less(regression_diff, 1.0 / sigma_squared),
            0.5 * sigma_squared * keras.backend.pow(regression_diff, 2),
            regression_diff - 0.5 / sigma_squared
        )

        # compute the normalizer: the number of positive anchors
        normalizer = keras.backend.maximum(1, keras.backend.shape(indices)[0])
        normalizer = keras.backend.cast(normalizer, dtype=keras.backend.floatx())
        return keras.backend.sum(regression_loss) / normalizer

    return _smooth_l1





# """


# Copyright 2017-2018 Fizyr (https://fizyr.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# """
#
# import keras
# from . import backend
# from keras import backend as k
# import tensorflow as tf
# import functools
# from keras.layers import Lambda
#
#
# def focal(alpha=0.25, gamma=2.0, center_alpha=0.03, num_calsses=9):
#     """ Create a functor for computing the focal loss.
#
#     Args
#         alpha: Scale the focal weight with alpha.
#         gamma: Take the power of the focal weight with gamma.
#
#     Returns
#         A functor that computes the focal loss using the alpha and gamma.
#     """
#     center = k.zeros([num_calsses,])
#
#     @functools.wraps(_focal)
#     def center_loss(y_true, y_pred):
#         return _focal(y_true, y_pred, alpha, gamma, center_alpha, num_calsses, center)
#
#     return center_loss
#
#
# def _focal(y_true, y_pred, alpha, gamma, center_alpha, num_classes, center):
#     """ Compute the focal loss given the target tensor and the predicted tensor.
#
#     As defined in https://arxiv.org/abs/1708.02002
#
#     Args
#         y_true: Tensor of target data from the generator with shape (B, N, num_classes).
#         y_pred: Tensor of predicted data from the network with shape (B, N, num_classes).
#
#     Returns
#         The focal loss of y_pred w.r.t. y_true.
#     """
#     labels = y_true[:, :, :-1]
#     anchor_state = y_true[:, :, -1]  # -1 for ignore, 0 for background, 1 for object
#     # split =Lambda( lambda x: tf.split(x,num_or_size_splits=2,axis=1) )(y_pred)
#     # split=tf.split(y_true,2)(y_pred)
#     classification = keras.layers.Activation('sigmoid', name="classification_loss")(y_pred)
#
#     # classification feature
#     feature = y_pred
#
#     # filter out "ignore" anchors
#     indices = backend.where(keras.backend.not_equal(anchor_state, -1))
#     labels = backend.gather_nd(labels, indices)
#
#     classification = backend.gather_nd(classification, indices)
#
#     feature = backend.gather_nd(feature, indices)
#
#     # compute the focal loss
#     alpha_factor = keras.backend.ones_like(labels) * alpha
#     alpha_factor = backend.where(keras.backend.equal(labels, 1), alpha_factor, 1 - alpha_factor)
#     focal_weight = backend.where(keras.backend.equal(labels, 1), 1 - classification, classification)
#     focal_weight = alpha_factor * focal_weight ** gamma
#
#     cls_loss = focal_weight * keras.backend.binary_crossentropy(labels, classification)
#     # compute the normalizer: the number of positive anchors
#     normalizer = backend.where(keras.backend.equal(anchor_state, 1))
#     normalizer = keras.backend.cast(keras.backend.shape(normalizer)[0], keras.backend.floatx())
#     normalizer = keras.backend.maximum(1.0, normalizer)
#
#     # compute the center loss
#     # labels = k.reshape(labels, [-1, 9])
#     labels = tf.to_int32(labels)
#     centers_batch = tf.gather(center, labels)
#
#     # diff = (1 - center_alpha) * (centers_batch - feature)
#     # center = tf.scatter_sub(center, labels, diff)
#     # loss = tf.reduce_mean(k.square(tf.to_float(labels) - centers_batch))
#     # loss += keras.backend.sum(cls_loss)
#     diff =  centers_batch - feature
#     # center = tf.scatter_sub(center, labels, diff)
#     loss = tf.reduce_mean(k.square(diff))*center_alpha
#     loss += keras.backend.sum(cls_loss)
#     return keras.backend.sum(loss) / normalizer
#
#
# def smooth_l1(sigma=3.0):
#     """ Create a smooth L1 loss functor.
#
#     Args
#         sigma: This argument defines the point where the loss changes from L2 to L1.
#
#     Returns
#         A functor for computing the smooth L1 loss given target data and predicted data.
#     """
#     sigma_squared = sigma ** 2
#
#     def _smooth_l1(y_true, y_pred):
#         """ Compute the smooth L1 loss of y_pred w.r.t. y_true.
#
#         Args
#             y_true: Tensor from the generator of shape (B, N, 5). The last value for each box is the state of the anchor (ignore, negative, positive).
#             y_pred: Tensor from the network of shape (B, N, 4).
#
#         Returns
#             The smooth L1 loss of y_pred w.r.t. y_true.
#         """
#         # separate target and state
#         regression = y_pred
#         regression_target = y_true[:, :, :-1]
#         anchor_state = y_true[:, :, -1]
#
#         # filter out "ignore" anchors
#         indices = backend.where(keras.backend.equal(anchor_state, 1))
#         regression = backend.gather_nd(regression, indices)
#         regression_target = backend.gather_nd(regression_target, indices)
#
#         # compute smooth L1 loss
#         # f(x) = 0.5 * (sigma * x)^2          if |x| < 1 / sigma / sigma
#         #        |x| - 0.5 / sigma / sigma    otherwise
#         regression_diff = regression - regression_target
#         regression_diff = keras.backend.abs(regression_diff)
#         regression_loss = backend.where(
#             keras.backend.less(regression_diff, 1.0 / sigma_squared),
#             0.5 * sigma_squared * keras.backend.pow(regression_diff, 2),
#             regression_diff - 0.5 / sigma_squared
#         )
#
#         # compute the normalizer: the number of positive anchors
#         normalizer = keras.backend.maximum(1, keras.backend.shape(indices)[0])
#         normalizer = keras.backend.cast(normalizer, dtype=keras.backend.floatx())
#         return keras.backend.sum(regression_loss) / normalizer
#
#     return _smooth_l1


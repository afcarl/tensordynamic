import numpy as np
import tensorflow as tf

from tensor_dynamic.layers.base_layer import BaseLayer
from tensor_dynamic.lazyprop import lazyprop
from tensor_dynamic.tf_loss_functions import squared_loss
from tensor_dynamic.utils import xavier_init, create_hessian_variable_op


class HiddenLayer(BaseLayer):
    def __init__(self, input_layer, output_nodes,
                 session=None,
                 bias=None,
                 weights=None,
                 back_bias=None,
                 bactivate=False,
                 freeze=False,
                 non_liniarity=None,
                 weight_extender_func=None,
                 weight_initializer_func=None,
                 bias_initializer_func=None,
                 input_noise_std=None,
                 bactivation_loss_func=None,
                 name='Layer'):
        super(HiddenLayer, self).__init__(input_layer,
                                          output_nodes,
                                          session=session,
                                          weight_extender_func=weight_extender_func,
                                          weight_initializer_func=weight_initializer_func,
                                          bias_initializer_func=bias_initializer_func,
                                          input_noise_std=input_noise_std,
                                          freeze=freeze,
                                          name=name)
        self._non_liniarity = self._get_property_or_default(non_liniarity, '_non_liniarity', tf.nn.sigmoid)
        self._bactivate = bactivate
        self._bactivation_loss_func = self._get_property_or_default(bactivation_loss_func, '_bactivation_loss_func',
                                                                    squared_loss)

        self._weights = self._create_variable("weights",
                                              (BaseLayer.INPUT_BOUND_VALUE, BaseLayer.OUTPUT_BOUND_VALUE),
                                              weights)

        self._bias = self._create_variable("bias",
                                           (BaseLayer.OUTPUT_BOUND_VALUE,),
                                           bias)

        if self.bactivate:
            self._back_bias = self._create_variable("back_bias",
                                                    (BaseLayer.INPUT_BOUND_VALUE,),
                                                    back_bias)
        else:
            self._back_bias = None

    @property
    def bactivate(self):
        return self._bactivate

    @property
    def kwargs(self):
        kwargs = super(HiddenLayer, self).kwargs

        kwargs['bactivate'] = self.bactivate
        kwargs['bactivation_loss_func'] = self._bactivation_loss_func
        kwargs['non_liniarity'] = self._non_liniarity

        return kwargs

    @property
    def has_bactivation(self):
        return self.bactivate

    def _layer_activation(self, input_activation, is_train):
        return self._non_liniarity(tf.matmul(input_activation, self._weights) + self._bias)

    def _layer_bactivation(self, activation, is_train):
        if self.bactivate:
            return self._non_liniarity(
                tf.matmul(activation, tf.transpose(self._weights)) + self._back_bias)

    @property
    def non_liniarity(self):
        return self._non_liniarity

    def supervised_cost_train(self, targets):
        if not self.next_layer:
            return tf.reduce_mean(tf.reduce_sum(tf.square(self.activation_train - targets), 1))
        else:
            return None

    @lazyprop
    def bactivation_loss_train(self):
        return tf.reduce_mean(tf.reduce_sum(tf.square(self.bactivation_train - self.input_layer.activation_train), 1))

    @lazyprop
    def bactivation_loss_predict(self):
        return tf.reduce_mean(
            tf.reduce_sum(tf.square(self.bactivation_predict - self.input_layer.activation_predict), 1))

    def has_resizable_dimension(self):
        return True

    def get_resizable_dimension_size(self):
        return self.output_nodes[0]

    def _get_node_importance(self):
        importance = self._session.run(self.activation_predict,
                                       feed_dict={self.input_placeholder:
                                                      np.ones(shape=(1,) + self.input_layer.output_nodes,
                                                              dtype=np.float32)})[0]
        return importance

    def _get_node_importance_hessian(self, features, labels):
        # TODO: Lazy prop these?
        weights_hessian_op = create_hessian_variable_op(self.last_layer.target_loss_op_train,
                                                        self._weights)

        bias_hessian_op = create_hessian_variable_op(self.last_layer.target_loss_op_train,
                                                     self._bias)

        weights_hessian, bias_hessian = self.session.run(
            [weights_hessian_op, bias_hessian_op],
            feed_dict={self.input_placeholder: features,
                       self.target_placeholder: labels}
        )

        node_importance = []

        for i in range(len(self.output_nodes[-1])):
            sum = bias_hessian[i]
            # TODO: Optimal brian damage recommends multiplying this by the value squared...
            for j in range(len(self.input_nodes[-1])):
                sum += weights_hessian[j][i]

            node_importance.append(sum)

        return node_importance


if __name__ == '__main__':
    with tf.Session() as session:
        input_p = tf.placeholder("float", (None, 10))
        layer = HiddenLayer(input_p, 20, session=session)
        layer.activation.get_shape()
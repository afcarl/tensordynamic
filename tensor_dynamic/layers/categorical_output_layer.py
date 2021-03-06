import tensorflow as tf

from tensor_dynamic.data.data_set import DataSet
from tensor_dynamic.layers.output_layer import OutputLayer
from tensor_dynamic.lazyprop import lazyprop, clear_lazyprop_on_lazyprop_cleared


class CategoricalOutputLayer(OutputLayer):
    def __init__(self, input_layer, output_nodes,
                 session=None,
                 bias=None,
                 weights=None,
                 back_bias=None,
                 freeze=False,
                 weight_extender_func=None,
                 layer_noise_std=None,
                 drop_out_prob=None,
                 batch_normalize_input=None,
                 batch_norm_transform=None,
                 batch_norm_scale=None,
                 regularizer_weighting=0.01,
                 regularizer_op=tf.nn.l2_loss,
                 loss_cross_entropy_or_log_prob=True,
                 save_checkpoints=0,
                 name='CategoricalOutputLayer'):
        super(CategoricalOutputLayer, self).__init__(input_layer, output_nodes,
                                                     session=session,
                                                     bias=bias,
                                                     weights=weights,
                                                     back_bias=back_bias,
                                                     freeze=freeze,
                                                     weight_extender_func=weight_extender_func,
                                                     layer_noise_std=layer_noise_std,
                                                     drop_out_prob=drop_out_prob,
                                                     batch_normalize_input=batch_normalize_input,
                                                     batch_norm_transform=batch_norm_transform,
                                                     batch_norm_scale=batch_norm_scale,
                                                     regularizer_weighting=regularizer_weighting,
                                                     regularizer_op=regularizer_op,
                                                     save_checkpoints=save_checkpoints,
                                                     name=name)
        self._loss_cross_entropy_or_log_prob = loss_cross_entropy_or_log_prob

    @lazyprop
    def _pre_softmax_activation_predict(self):
        clear_lazyprop_on_lazyprop_cleared(self, '_pre_softmax_activation_predict', self.input_layer,
                                           'activation_predict')
        with self.name_scope(is_predict=True):
            input_activation = self._process_input_activation_predict(self.input_layer.activation_predict)
            return self._layer_activation(input_activation, False)

    @lazyprop
    def _pre_softmax_activation_train(self):
        clear_lazyprop_on_lazyprop_cleared(self, '_pre_softmax_activation_train', self.input_layer,
                                           'activation_train')
        with self.name_scope(is_train=True):
            input_activation = self._process_input_activation_train(self.input_layer.activation_train)
            return self._layer_activation(input_activation, True)

    @lazyprop
    def activation_predict(self):
        clear_lazyprop_on_lazyprop_cleared(self, 'activation_predict', self.input_layer, 'activation_predict')
        with self.name_scope(is_predict=True):
            return tf.nn.softmax(self._pre_softmax_activation_predict)

    @lazyprop
    def activation_train(self):
        clear_lazyprop_on_lazyprop_cleared(self, 'activation_train', self.input_layer, 'activation_train')
        with self.name_scope(is_train=True):
            return tf.nn.softmax(self._pre_softmax_activation_train)

    @lazyprop
    def target_loss_op_train(self):
        clear_lazyprop_on_lazyprop_cleared(self, 'target_loss_op_train', self.input_layer)
        with self.name_scope(is_train=True):
            return self._target_loss_op(self._pre_softmax_activation_train)

    @lazyprop
    def target_loss_op_predict(self):
        clear_lazyprop_on_lazyprop_cleared(self, 'target_loss_op_predict', self.input_layer)
        with self.name_scope(is_predict=True):
            return self._target_loss_op(self._pre_softmax_activation_predict)

    def _target_loss_op(self, input_tensor):
        if self._loss_cross_entropy_or_log_prob:
            loss = tf.nn.softmax_cross_entropy_with_logits(logits=input_tensor, labels=self._target_placeholder)
        else:
            loss = -tf.log(tf.reduce_sum(tf.nn.softmax(input_tensor) * self.target_placeholder, 1))

        return tf.reduce_sum(loss)

    @lazyprop
    def accuracy_op(self):
        clear_lazyprop_on_lazyprop_cleared(self, 'accuracy_op', self.input_layer)
        return tf.reduce_mean(tf.cast(tf.nn.in_top_k(self._pre_softmax_activation_predict, tf.argmax(self.target_placeholder, 1), 1),
                                      tf.float32))

    def accuracy(self, data_set):
        """Get the accuracy of our predictions against the real targets, returns a value in the range 0. to 1.

        Args:
            data_set (DataSet):

        Returns:
            float: accuracy in the range 0. to 1.
        """
        assert isinstance(data_set, DataSet)

        return self.session.run(self.accuracy_op,
                                feed_dict={self.input_placeholder: data_set.features,
                                           self._target_placeholder: data_set.labels})

    @lazyprop
    def log_probability_of_targets_op(self):
        clear_lazyprop_on_lazyprop_cleared(self, 'log_probability_of_targets_op', self.input_layer)
        return tf.reduce_sum(tf.log(tf.reduce_sum(tf.nn.softmax(self.activation_predict) * self.target_placeholder, 1)))

    @property
    def regularizable_variables(self):
        yield self._weights

    @property
    def kwargs(self):
        kwargs = super(OutputLayer, self).kwargs

        del kwargs['bactivate']
        del kwargs['bactivation_loss_func']
        del kwargs['non_liniarity']

        kwargs['loss_cross_entropy_or_log_prob'] = self._loss_cross_entropy_or_log_prob

        return kwargs
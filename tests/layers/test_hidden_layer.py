import numpy as np
import tensorflow as tf
from math import log

from tensor_dynamic.layers.categorical_output_layer import CategoricalOutputLayer
from tensor_dynamic.layers.input_layer import InputLayer
from tensor_dynamic.layers.hidden_layer import HiddenLayer
from tensor_dynamic.node_importance import node_importance_optimal_brain_damage
from tests.layers.base_layer_testcase import BaseLayerWrapper


class TestHiddenLayer(BaseLayerWrapper.BaseLayerTestCase):
    def _create_layer_for_test(self):
        return HiddenLayer(self._input_layer, self.OUTPUT_NODES, session=self.session)

    def test_create_layer(self):
        output_nodes = 20
        input_p = tf.placeholder("float", (None, 10))
        layer = HiddenLayer(InputLayer(input_p), output_nodes, session=self.session)

        self.assertEqual(layer.activation_predict.get_shape().as_list(), [None, output_nodes])

    def test_create_extra_weight_dimensions(self):
        output_nodes = 2
        input_p = tf.placeholder("float", (None, 2))
        layer = HiddenLayer(InputLayer(input_p), output_nodes, session=self.session,
                            weights=np.array([[100.0]], dtype=np.float32))

        self.assertEqual(layer._weights.get_shape().as_list(), [2, 2])

    def test_reshape(self):
        output_nodes = 2
        input_p = tf.placeholder("float", (None, 2))
        layer = HiddenLayer(InputLayer(input_p), output_nodes, session=self.session,
                            weights=np.array([[100.0]], dtype=np.float32))

        result1 = self.session.run(layer.activation_predict, feed_dict={layer.input_placeholder: [[1., 1.]]})

        layer.resize(3)
        result2 = self.session.run(layer.activation_predict, feed_dict={layer.input_placeholder: [[1., 1.]]})

        print(result1)
        print(result2)

        self.assertEquals(len(result2[0]), 3)

    def test_create_extra_weight_dimensions_fail_case(self):
        output_nodes = 2
        input_p = tf.placeholder("float", (None, 4))
        layer = HiddenLayer(InputLayer(input_p), output_nodes, session=self.session,
                            weights=np.array([[10., 10.],
                                              [10., 10.],
                                              [10., 10.]], dtype=np.float32))

        self.assertEqual(layer._weights.get_shape().as_list(), [4, 2])

    def test_resize(self):
        output_nodes = 10
        input_p = tf.placeholder("float", (None, 10))
        layer = HiddenLayer(InputLayer(input_p), output_nodes, session=self.session)
        layer.resize(output_nodes + 1)

        print layer._bias.get_shape()

        self.assertEqual(layer.activation_predict.get_shape().as_list(), [None, output_nodes + 1])
        self.assertEquals(layer.output_nodes, (output_nodes + 1,))

    def test_get_output_layer_activation(self):
        input_p = tf.placeholder("float", (None, 10))
        layer = HiddenLayer(InputLayer(input_p), 1, session=self.session)
        layer2 = HiddenLayer(layer, 2, session=self.session)
        layer3 = HiddenLayer(layer2, 3, session=self.session)

        self.assertEquals(layer.last_layer.activation_predict, layer3.activation_predict)

    def test_layer_noisy_input_activation(self):
        input_size = 100
        noise_std = 1.
        input_p = tf.placeholder("float", (None, input_size))
        layer = HiddenLayer(InputLayer(input_p), input_size,
                            weights=np.diag(np.ones(input_size, dtype=np.float32)),
                            bias=np.zeros(input_size, dtype=np.float32),
                            session=self.session,
                            non_liniarity=tf.identity,
                            layer_noise_std=noise_std)

        result_noisy = self.session.run(layer.activation_train,
                                        feed_dict={
                                            input_p: np.ones(input_size, dtype=np.float32).reshape((1, input_size))})

        self.assertAlmostEqual(result_noisy.std(), noise_std, delta=noise_std / 5.,
                               msg="the result std should be the noise_std")

        result_clean = self.session.run(layer.activation_predict, feed_dict={
            input_p: np.ones(input_size, dtype=np.float32).reshape((1, input_size))})

        self.assertAlmostEqual(result_clean.std(), 0., places=7,
                               msg="There should be no noise in the activation")

    def test_layer_noisy_input_bactivation(self):
        input_size = 100
        noise_std = 1.
        input_p = tf.placeholder("float", (None, input_size))
        layer = HiddenLayer(InputLayer(input_p), input_size,
                            weights=np.diag(np.ones(input_size, dtype=np.float32)),
                            bias=np.zeros(input_size, dtype=np.float32),
                            back_bias=np.zeros(input_size, dtype=np.float32),
                            session=self.session,
                            bactivate=True,
                            non_liniarity=tf.identity,
                            layer_noise_std=noise_std)

        result_noisy = self.session.run(layer.bactivation_train,
                                        feed_dict={
                                            input_p: np.ones(input_size, dtype=np.float32).reshape((1, input_size))})

        self.assertAlmostEqual(result_noisy.std(), noise_std, delta=noise_std / 4.,
                               msg="the result std should be the noise_std")

        result_clean = self.session.run(layer.bactivation_predict, feed_dict={
            input_p: np.ones(input_size, dtype=np.float32).reshape((1, input_size))})

        self.assertAlmostEqual(result_clean.std(), 0., delta=0.1,
                               msg="When running in prediction mode there should be no noise in the bactivation")

    def test_more_nodes_improves_reconstruction_loss(self):
        recon_1 = self.reconstruction_loss_for(1)
        recon_2 = self.reconstruction_loss_for(2)
        self.assertLess(recon_2, recon_1)
        recon_5 = self.reconstruction_loss_for(5)
        self.assertLess(recon_5, recon_2)
        recon_20 = self.reconstruction_loss_for(20)
        self.assertLess(recon_20, recon_5)

    def reconstruction_loss_for(self, output_nodes):
        data = self.mnist_data
        input_layer = InputLayer(784)
        bw_layer1 = HiddenLayer(input_layer, output_nodes, session=self.session, layer_noise_std=1.0, bactivate=True)

        cost_train = tf.reduce_mean(
            tf.reduce_sum(tf.square(bw_layer1.bactivation_train - input_layer.activation_train), 1))
        cost_predict = tf.reduce_mean(
            tf.reduce_sum(tf.square(bw_layer1.bactivation_predict - input_layer.activation_predict), 1))
        optimizer = tf.train.AdamOptimizer(0.01).minimize(cost_train)

        self.session.run(tf.initialize_all_variables())

        end_epoch = data.train.epochs_completed + 3

        while data.train.epochs_completed <= end_epoch:
            train_x, train_y = data.train.next_batch(100)
            self.session.run(optimizer, feed_dict={bw_layer1.input_placeholder: train_x})

        result = self.session.run(cost_predict,
                                  feed_dict={bw_layer1.input_placeholder: data.test.features})
        print("denoising with %s hidden layer had cost %s" % (output_nodes, result))
        return result

    def test_reconstruction_of_single_input(self):
        input_layer = InputLayer(1)
        layer = HiddenLayer(input_layer, 1, bactivate=True, session=self.session, layer_noise_std=0.3)

        cost_train = tf.reduce_mean(
            tf.reduce_sum(tf.square(layer.bactivation_train - input_layer.activation_train), 1))
        cost_predict = tf.reduce_mean(
            tf.reduce_sum(tf.square(layer.bactivation_predict - input_layer.activation_predict), 1))
        optimizer = tf.train.AdamOptimizer(0.1).minimize(cost_train)

        self.session.run(tf.initialize_all_variables())

        data = np.random.normal(0.5, 0.5, size=[200, 1])

        for x in range(100):
            self.session.run([optimizer], feed_dict={input_layer.input_placeholder: data})

        result = self.session.run([cost_predict], feed_dict={input_layer.input_placeholder: data})
        print result

    def test_noise_reconstruction(self):
        INPUT_DIM = 10
        HIDDEN_NODES = 1
        input_layer = InputLayer(INPUT_DIM)
        bw_layer1 = HiddenLayer(input_layer, HIDDEN_NODES, session=self.session, layer_noise_std=1.0,
                                bactivate=True)

        # single cluster reconstruct
        data = []
        for i in range(10):
            data.append([i * .1] * INPUT_DIM)

        cost_train = tf.reduce_mean(
            tf.reduce_sum(tf.square(bw_layer1.bactivation_train - input_layer.activation_train), 1))
        cost_predict = tf.reduce_mean(
            tf.reduce_sum(tf.square(bw_layer1.bactivation_predict - input_layer.activation_predict), 1))
        optimizer = tf.train.AdamOptimizer(0.01).minimize(cost_train)

        self.session.run(tf.initialize_all_variables())

        for j in range(200):
            self.session.run(optimizer, feed_dict={bw_layer1.input_placeholder: data})

        result = self.session.run(cost_predict,
                                  feed_dict={bw_layer1.input_placeholder: data})

        print("denoising with %s hidden layer had cost %s" % (HIDDEN_NODES, result))

    def test_find_best_layer_size(self):
        data = self.mnist_data
        input_layer = InputLayer(data.features_shape)
        layer = HiddenLayer(input_layer, 10, session=self.session, layer_noise_std=1.0, bactivate=False)
        output = CategoricalOutputLayer(layer, data.labels_shape)

        layer.find_best_size(data.train, data.test,
                             lambda m, d: output.evaluation_stats(d)[0] - log(output.get_parameters_all_layers()),
                             initial_learning_rate=0.1, tuning_learning_rate=0.01)

        assert layer.get_resizable_dimension_size() > 10

    # TODO: Move to categorical output layer
    # def test_learn_struture(self):
    #     data = self.mnist_data
    #     input_layer = InputLayer(data.features_shape)
    #     layer = HiddenLayer(input_layer, 10, session=self.session, input_noise_std=1.0, bactivate=False)
    #     output = CategoricalOutputLayer(layer, data.labels_shape)
    #
    #     output.learn_structure_random(data.train, data.test)
    #
    #     assert layer.get_resizable_dimension_size() > 10

    def test_remove_unimportant_nodes_does_not_affect_test_error(self):
        data = self.mnist_data
        input_layer = InputLayer(data.features_shape)
        layer = HiddenLayer(input_layer, 500, session=self.session,
                            node_importance_func=node_importance_optimal_brain_damage)
        output = CategoricalOutputLayer(layer, data.labels_shape, regularizer_weighting=0.0001)

        output.train_till_convergence(data.train, learning_rate=0.01)

        _, _, target_loss_before_resize = output.evaluation_stats(data.test) # Should this be on test or train?

        print(target_loss_before_resize)

        layer.resize(450, data_set=data.test)

        _, _, target_loss_after_resize = output.evaluation_stats(data.test)

        print(target_loss_after_resize)

        self.assertAlmostEqual(target_loss_before_resize, target_loss_after_resize, places=2)
import numpy as np
import tensorflow as tf

from tensor_dynamic.layers.input_layer import InputLayer
from tensor_dynamic.tests.base_tf_testcase import BaseTfTestCase


class BaseLayerWrapper(object):
    def __init__(self):
        """
        This class only exists so base tests aren't run on there own
        """
        pass

    class BaseLayerTestCase(BaseTfTestCase):
        INPUT_NODES = 10
        OUTPUT_NODES = 6

        def setUp(self):
            super(BaseLayerWrapper.BaseLayerTestCase, self).setUp()
            self._input_placeholder = tf.placeholder("float", shape=(None, self.INPUT_NODES))
            self._input_layer = InputLayer(self._input_placeholder)
            self._target_placeholder = tf.placeholder("float", shape=(None, self.OUTPUT_NODES))

        def _createLayerForTest(self):
            raise NotImplementedError('Override in sub class to return a new instance of the layer to be tested')

        def test_clone(self):
            layer = self._createLayerForTest()
            clone = layer.clone()
            input_noise = np.random.normal(size=[1, layer.input_nodes])
            layer_activation = self.session.run(layer.activation_predict,
                                                feed_dict={layer.input_placeholder: input_noise})
            clone_activation = self.session.run(clone.activation_predict,
                                                feed_dict={layer.input_placeholder: input_noise})

            np.testing.assert_array_almost_equal(
                layer_activation, clone_activation,
                err_msg="Expect activation to be unchanged after cloning, but found difference")

            if layer.bactivate:
                layer_activation = self.session.run(layer.bactivation,
                                                    feed_dict={layer.input_placeholder: input_noise})
                clone_activation = self.session.run(clone.activation_predict,
                                                    feed_dict={layer.input_placeholder: input_noise})

                np.testing.assert_array_almost_equal(
                    layer_activation, clone_activation,
                    err_msg="Expect activation to be unchanged after cloning, but found difference")

        def test_resize(self):
            layer = self._createLayerForTest()

            input_noise = np.random.normal(size=[1, layer.input_nodes])
            layer_activation = self.session.run(layer.activation_predict,
                                                feed_dict={layer.input_placeholder: input_noise})

            layer.resize()

            layer_activation_post_resize = self.session.run(layer.activation_predict,
                                                            feed_dict={layer.input_placeholder: input_noise})

            self.assertEqual(layer_activation.shape[-1]+1, layer_activation_post_resize.shape[-1])
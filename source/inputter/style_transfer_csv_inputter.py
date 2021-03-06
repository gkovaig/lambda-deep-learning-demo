"""
Copyright 2018 Lambda Labs. All Rights Reserved.
Licensed under
==========================================================================

"""
from __future__ import print_function
import os
import csv

import tensorflow as tf

from .inputter import Inputter
from source.augmenter.external import vgg_preprocessing


class StyleTransferCSVInputter(Inputter):
  def __init__(self, config, augmenter):
    super(StyleTransferCSVInputter, self).__init__(config, augmenter)

    self.num_samples = -1

    if self.config.mode == "infer":
      self.test_samples = self.config.test_samples

  def create_nonreplicated_fn(self):
    batch_size = (self.config.batch_size_per_gpu *
                  self.config.gpu_count)
    max_step = (self.get_num_samples() * self.config.epochs // batch_size)
    tf.constant(max_step, name="max_step")

  def get_num_samples(self):
    if self.num_samples < 0:
      if self.config.mode == "infer":
        self.num_samples = len(self.test_samples)
      elif self.config.mode == "export":
        self.num_samples = 1           
      else:
        self.num_samples = 0
        for meta in self.config.dataset_meta:
          with open(meta) as f:
            parsed = csv.reader(f, delimiter=",", quotechar="'")
            self.num_samples += len(list(parsed))          
    return self.num_samples

  def get_samples_fn(self):
    if self.config.mode == "infer":
      images_path = self.test_samples
    elif self.config.mode == "train" or \
            self.config.mode == "eval":
      for meta in self.config.dataset_meta:
        assert os.path.exists(meta), (
          "Cannot find dataset_meta file {}.".format(meta))

      images_path = []

      for meta in self.config.dataset_meta:
        dirname = os.path.dirname(meta)
        with open(meta) as f:
          parsed = csv.reader(f, delimiter=",", quotechar="'")
          for row in parsed:
            images_path.append(os.path.join(dirname, row[0]))

    return (images_path,)

  def parse_fn(self, image_path):
    """Parse a single input sample
    """
    image = tf.read_file(image_path)
    image = tf.image.decode_jpeg(image,
                                 channels=self.config.image_depth,
                                 dct_method="INTEGER_ACCURATE")

    if self.config.mode == "infer":
      image = tf.to_float(image)
      image = vgg_preprocessing._mean_image_subtraction(image)
    else:
      if self.augmenter:
        is_training = (self.config.mode == "train")
        image = self.augmenter.augment(
          image,
          self.config.image_height,
          self.config.image_width,
          self.config.resize_side_min,
          self.config.resize_side_max,
          is_training=is_training,
          speed_mode=self.config.augmenter_speed_mode)
    return (image,)

  def input_fn(self, test_samples=[]):
    if self.config.mode == "export":
      image = tf.placeholder(tf.float32,
                             shape=(None, None, 3),
                             name="input_image")      
      image = tf.to_float(image)
      image = vgg_preprocessing._mean_image_subtraction(image)
      image = tf.expand_dims(image, 0)
      return image
    else:
      batch_size = (self.config.batch_size_per_gpu *
                    self.config.gpu_count)

      samples = self.get_samples_fn()

      dataset = tf.data.Dataset.from_tensor_slices(samples)

      if self.config.mode == "train":
        dataset = dataset.shuffle(self.get_num_samples())

      dataset = dataset.repeat(self.config.epochs)

      dataset = dataset.map(
        lambda image: self.parse_fn(image),
        num_parallel_calls=4)

      dataset = dataset.apply(
          tf.contrib.data.batch_and_drop_remainder(batch_size))

      dataset = dataset.prefetch(2)

      iterator = dataset.make_one_shot_iterator()
      return iterator.get_next()


def build(config, augmenter):
  return StyleTransferCSVInputter(config, augmenter)

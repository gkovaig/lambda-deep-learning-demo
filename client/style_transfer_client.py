# Copyright 2018 Google Inc. All Rights Reserved.
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
# ==============================================================================
"""A client that performs inferences on a ResNet model using the REST API.

Install nvidia-docker
https://github.com/NVIDIA/nvidia-docker#quick-start

Typical usage example:
docker run --runtime=nvidia -p 8501:8501 \
--name tfserving_styletransfer \
--mount type=bind,source=/home/ubuntu/demo/model/fns_gothic_20190126/export,target=/models/styletransfer \
-e MODEL_NAME=styletransfer -t tensorflow/serving:latest-gpu &


python client/style_transfer_client.py --image_path=/home/ubuntu/demo/data/mscoco_fns/val2014/COCO_val2014_000000301397.jpg
"""

from __future__ import print_function

import requests
import numpy as np
import json
import argparse
import os
import skimage.io
from skimage.transform import resize
from skimage.transform import rescale
from skimage import img_as_ubyte
import matplotlib.pyplot as plt
from PIL import Image

# The server URL specifies the endpoint of your server running the ResNet
# model with the name "resnet" and using the predict interface.
SERVER_URL = 'http://localhost:8501/v1/models/styletransfer:predict'


def main():

  parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  parser.add_argument("--image_path",
                      help="path for image to run inference",
                      default="~/demo/data/mscoco_fns/val2014/COCO_val2014_000000301397.jpg")

  args = parser.parse_args()

  args.image_path = os.path.expanduser(args.image_path)

  # Read the image
  image = skimage.io.imread(args.image_path, plugin='imageio')
  image = rescale(image, 2.0, anti_aliasing=False)
  image = img_as_ubyte(image)

  data = json.dumps({"signature_name": "predict", "instances": image.tolist()})
  headers = {"content-type": "application/json"}

  response = requests.post(SERVER_URL, data=data, headers=headers)
  response.raise_for_status()

  predictions = np.squeeze(
    np.array(response.json()["predictions"]), axis=0)
  
  render_image = Image.fromarray(img_as_ubyte(predictions / 255.0), 'RGB')
  plt.imshow(render_image)
  plt.show()


if __name__ == '__main__':
  main()

import numpy as np
import cv2
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(os.path.join(parent_dir, 'tools'))
from pickle_dataset import merge_pickled_dictionaries

from sklearn.externals import joblib
"""
Adapted from https://github.com/kratzert/finetune_alexnet_with_tensorflow/blob/master/datagenerator.py
"""


class ImageDataGenerator:
    """ Set read_as_pickle as True to read file class_list as joblib file and
        therefore load images and labels. Set it to False to read file
        class_list as a file generated by split_dataset in
        split_dataset_with_labels_world.py
            [path_to_line center_of_line (3x) line_type label] on each line.
    Args:
        class_list (list of string):
            * If read_as_pickle == True: List of the paths of the pickle files
                from which the data should be loaded.
            * If read_as_pickle == False: List of the paths of the text files
                that contain the location and other information of the data that
                should be loaded.
        horizontal_flip (bool): If True, input images are horizontally flipped
            with a probability of 50% before being fed to the network.
        shuffle (bool): If True, the input images (and corresponding line types
            and labels) are rearranged in random order.
        image_type (string): Either 'bgr' or 'bgr-d'. Type of the input images.
        mean (numpy array of shape (num_channels, ) where num_channels is 3 if
            self.image_type is 'bgr' and 4 if self.image_type is 'bgr-d'):
            Channelwise mean of the images in the input data.
        scale_size (tuple of int): Size to which the input images should be
            scaled before feeding them to the network.
        read_as_pickle (bool): If True, the input data is read from a set of
            pickle files, otherwise it is read by loading the images from disk
            based on the locations specified in class_list.
    Attributes:
        horizontal_flip (bool): If True, input images are horizontally flipped
            with a probability of 50% before being fed to the network.
        shuffle (bool): If True, the input images (and corresponding line types
            and labels) are rearranged in random order.
        image_type (string): Either 'bgr' or 'bgr-d'. Type of the input images.
        mean (numpy array of shape (num_channels, ) where num_channels is 3 if
            self.image_type is 'bgr' and 4 if self.image_type is 'bgr-d'):
            Channelwise mean of the images in the input data.
        scale_size (tuple of int): Size to which the input images should be
            scaled before feeding them to the network.
        read_as_pickle (bool): If True, the input data is read from a set of
            pickle files, otherwise it is read by loading the images from disk
            based on the locations specified in class_list.
        pointer (int): Internal pointer that advances when a new batch is fed to
            the network.
    """

    def __init__(self,
                 class_list,
                 horizontal_flip=False,
                 shuffle=False,
                 image_type='bgr',
                 mean,
                 scale_size=(227, 227),
                 read_as_pickle=False):
        # Initialize parameters.
        self.horizontal_flip = horizontal_flip
        self.shuffle = shuffle
        self.image_type = image_type
        if image_type not in ['bgr', 'bgr-d']:
            raise ValueError("Images should be 'bgr' or 'bgr-d'")
        elif image_type == 'bgr':
            assert (mean.shape[0] == 3)
        elif image_type == 'bgr-d':
            assert (mean.shape[0] == 4)
        self.mean = mean
        self.scale_size = scale_size
        self.pointer = 0
        self.read_as_pickle = read_as_pickle

        if read_as_pickle:
            self.read_class_list_as_pickle(class_list)
        else:
            self.read_class_list_as_path_and_labels(class_list)

        if self.shuffle:
            self.shuffle_data()

    def read_class_list_as_pickle(self, class_list):
        """ Loads images, labels and line types to memory from the input pickle
            files.
        Args:
            class_list (list of string): List of the paths of the pickle files
                from which the data should be loaded.
        """
        pickled_dict = {}
        # Merge dictionaries extracted from all the pickle files in class_list.
        for file_ in class_list:
            temp_dict = joblib.load(file_)
            merge_pickled_dictionaries(pickled_dict, temp_dict)
        self.pickled_images_bgr = []
        self.pickled_images_depth = []
        self.pickled_labels = []
        self.line_types = []
        for dataset_name in pickled_dict.keys():
            dataset_name_dict = pickled_dict[dataset_name]
            for trajectory_number in dataset_name_dict.keys():
                trajectory_number_dict = dataset_name_dict[trajectory_number]
                for frame_number in trajectory_number_dict.keys():
                    frame_number_dict = trajectory_number_dict[frame_number]
                    for image_type in frame_number_dict.keys():
                        image_type_dict = frame_number_dict[image_type]
                        for line_number in image_type_dict.keys():
                            line_number_dict = image_type_dict[line_number]
                            # Append image.
                            if image_type == 'rgb':
                                # Append label.
                                self.pickled_labels.append(
                                    line_number_dict['labels'])
                                self.pickled_images_bgr.append(
                                    line_number_dict['img'])
                            elif image_type == 'depth':
                                self.pickled_images_depth.append(
                                    line_number_dict['img'])
                            # Append line type.
                            self.line_types.append(
                                line_number_dict['line_type'])
        # Store total number of data of lines in the dataset.
        self.data_size = len(self.pickled_labels)
        self.access_indices = np.array(range(self.data_size))
        print('Just set data_size to be {0}'.format(self.data_size))

    def read_class_list_as_path_and_labels(self, class_list):
        """ Old version of the data loader, kept here for backcompatibility.
            Loads images, labels and line types to memory by reading the
            location of the data on the disk from an input text file.
        Args:
            class_list (list of string): List of the paths of the text files
                that contain the location and other information of the data that
                should be loaded. Only the first file in the list will be
                actually used, because a functionality to handle more than one
                file still needs to be implemented.
        """
        # In non-pickle mode read only first file in the list.
        with open(class_list[0]) as f:
            lines = f.readlines()
            self.images = []
            self.labels = []
            self.line_types = []
            for l in lines:
                items = l.split()
                self.images.append(items[0])
                self.labels.append([float(i)
                                    for i in items[1:-2]] + [float(items[-1])])
                self.line_types.append(float(items[-2]))

            # Store total number of data.
            self.data_size = len(self.labels)

    def shuffle_data(self):
        """ Randomly shuffles the data stored.
        """
        if self.read_as_pickle:
            # Indices that encode the order in which the dataset is accessed.
            idx = np.random.permutation(len(self.pickled_labels))
            self.access_indices = idx
        else:
            images = list(self.images)
            labels = list(self.labels)
            line_types = list(self.line_types)
            self.images = []
            self.labels = []
            self.line_types = []
            idx = np.random.permutation(len(labels))

            for i in idx:
                self.images.append(images[i])
                self.labels.append(labels[i])
                self.line_types.append(line_types[i])

    def reset_pointer(self):
        """ Resets internal pointer to point to the beginning of the stored
            data.
        """
        self.pointer = 0

        if self.shuffle:
            self.shuffle_data()

    def set_pointer(self, index):
        """ Sets the internal pointer to point to the given index.
        Args:
            index (int): Index to which the internal pointer should point.
        """
        self.pointer = index

    def next_batch(self, batch_size):
        """ Forms a batch of size batch_size, returning for each line in the
            batch its virtual camera image, its label ([Center point 3x],
            [Instance label 1x]) and its line type.
        Args:
            batch_size (int): Size of the batch to generate.

        Returns:
            images (numpy array of shape (batch_size, self.scale_size[0],
                self.scale_size[1], num_channels), where num_channels is 3 if
                self.image_type is 'bgr' and 4 if self.image_type is 'bgr-d'):
                images[i, :, :, :] contains the virtual image associated to the
                i-th line in the batch.
            labels (numpy array of shape (batch_size, 4) and dtype np.float32):
                labels[i, :] contains the label ([Center point 3x],
                [Instance label 1x]) of the i-th line in the batch.
            line_types (numpy array of shape (batch_size, 1) and dtype
                np.float32): line_types[i, :] contains the line type of the i-th
                line in the batch (0.: Discontinuity line, 1.: Planar line,
                2.: Edge line, 3.: Intersection line).
        """
        # Allocate memory for the batch of images.
        if self.image_type == 'bgr':
            images = np.ndarray(
                [batch_size, self.scale_size[0], self.scale_size[1], 3])
        elif self.image_type == 'bgr-d':
            images = np.ndarray(
                [batch_size, self.scale_size[0], self.scale_size[1], 4])

        if self.read_as_pickle:
            labels = []
            line_types = []
            # Get next batch of image, labels and line types.
            for i in range(self.pointer, self.pointer + batch_size):
                # Retrieve access index in the order defined (data can be
                # shuffled with shuffle_data()).
                idx = self.access_indices[i]
                if self.image_type == 'bgr':
                    # BGR image.
                    img = self.pickled_images_bgr[idx]
                elif self.image_type == 'bgr-d':
                    # BGR-D image.
                    img = np.dstack([
                        self.pickled_images_bgr[idx],
                        self.pickled_images_depth[idx]
                    ])
                # Flip image at random if flag is selected.
                if self.horizontal_flip and np.random.random() < 0.5:
                    img = cv2.flip(img, 1)

                # Rescale image so as to match desired scale size.
                img = cv2.resize(img, (self.scale_size[0], self.scale_size[1]))
                img = img.astype(np.float32)

                # Subtract mean of training set.
                img -= self.mean

                # Append image, label and line type to the outputs.
                images[i - self.pointer] = img
                labels.append(self.pickled_labels[idx])
                line_types.append(self.line_types[idx])
        else:
            # Get next batch of image (by retrieving its path), labels and line
            # types.
            paths = self.images[self.pointer:self.pointer + batch_size]
            labels = self.labels[self.pointer:self.pointer + batch_size]
            line_types = self.line_types[self.pointer:self.pointer + batch_size]

            # Read images.
            for i in range(len(paths)):
                if self.image_type == 'bgr':
                    # BGR image.
                    img = cv2.imread(paths[i], cv2.IMREAD_UNCHANGED)
                elif self.image_type == 'bgr-d':
                    path_rgb = paths[i]
                    path_depth = path_rgb.replace('rgb', 'depth')
                    img_bgr = cv2.imread(path_rgb, cv2.IMREAD_UNCHANGED)
                    img_depth = cv2.imread(path_depth, cv2.IMREAD_UNCHANGED)
                    # BGR-D image.
                    img = np.dstack([img_bgr, img_depth])

                # Flip image at random if flag is selected.
                if self.horizontal_flip and np.random.random() < 0.5:
                    img = cv2.flip(img, 1)

                # Rescale image so as to match desired scale size.
                img = cv2.resize(img, (self.scale_size[0], self.scale_size[1]))
                img = img.astype(np.float32)

                # Subtract mean of training set.
                img -= self.mean

                # Append image to the output.
                images[i] = img

        # Update pointer.
        self.pointer += batch_size

        # Convert labels and line types to numpy arrays.
        labels = np.array(labels, dtype=np.float32)
        line_types = np.asarray(
            line_types, dtype=np.float32).reshape(batch_size, -1)
        # Normalize line_types from values in {0, 1, 2, 3} to values in [-1, 1]:
        # - Zero-center by subtracting mean (1.5)
        # - Normalize the interval ([-1.5, 1.5]) to [-1, 1] (divide by 1.5)
        line_types = (line_types - 1.5) / 1.5
        if self.read_as_pickle:
            assert labels.shape == (batch_size, 7)
        else:
            assert labels.shape == (batch_size, 4)

        # Return array of images, labels and line types.
        return images, labels, line_types

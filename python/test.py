import sys
import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt

from model.datagenerator import ImageDataGenerator
from tools.visualization import vis_square
from tools.get_line_center import get_line_center

python_root = '../'
sys.path.insert(0, python_root)

log_files_folder = '/media/francesco/line tools data/logs/15112018_0824/'

sess = tf.InteractiveSession()
saver = tf.train.import_meta_graph(
    os.path.join(log_files_folder,
                 'triplet_loss_batch_all_ckpt/bgr-d_model_epoch10.ckpt.meta')
    #os.path.join(log_files_folder,
    #             'triplet_loss_batch_all_ckpt/model_epoch100.ckpt.meta')
)
saver.restore(
    sess,
    os.path.join(log_files_folder,
                 'triplet_loss_batch_all_ckpt/bgr-d_model_epoch10.ckpt')
    #os.path.join(log_files_folder,
    #             'triplet_loss_batch_all_ckpt/model_epoch100.ckpt')
)

# Visualize kernels
conv1_kernels = sess.run('conv1/weights:0')
conv1_kernels_rgb = conv1_kernels[:, :, :3, :]
conv1_kernels_depth = conv1_kernels[:, :, -1, :]

plt.rcParams['figure.figsize'] = (10, 10)

vis_square(conv1_kernels_rgb.transpose(3, 0, 1, 2))
vis_square(conv1_kernels_depth.transpose(2, 0, 1))

read_as_pickle = True

test_files = '/media/francesco/line tools data/pickle files/train/traj_1/pickled_test.pkl'
#test_files = '/media/francesco/line tools data/pickle files/train/traj_1/test.txt'
#test_files = '/media/francesco/line tools data/pickle files/train/traj_2/test_edited.txt'

# For the last models trained, that also store train_set_mean in the model
train_set_mean = sess.run('train_set_mean:0')

# 0611180855
#train_set_mean = np.array([22.26707982, 22.24587975, 19.15592466, 668.46125445])
# 1311181041
#train_set_mean = np.array([21.3586346, 19.12882567, 5.41484424, 601.17042995])
# Chengkun's
#train_set_mean = np.array([22.4536157, 20.11461999, 5.61416132, 605.87199598])

print("Train set mean is {}".format(train_set_mean))

test_generator = ImageDataGenerator(
    [test_files],
    image_type='bgr-d',
    mean=train_set_mean,
    read_as_pickle=read_as_pickle)

# Check if embeddings have already been generated. If not generate them
embeddings_path = os.path.join(log_files_folder, 'embeddings.npy')
if os.path.isfile(embeddings_path):
    print("Using embeddings found at {}".format(embeddings_path))
    test_embeddings_all = np.load(embeddings_path)
else:
    graph = tf.get_default_graph()
    x = graph.get_tensor_by_name('Placeholder:0')  # input images
    labels = graph.get_tensor_by_name(
        'Placeholder_1:0')  # labels of input images
    keep_prob = graph.get_tensor_by_name(
        'Placeholder_2:0')  # dropout probability
    embeddings = graph.get_tensor_by_name('l2_normalize:0')

    batch_size = int(x.shape[0])
    test_embeddings_all = np.empty(
        (0, int(embeddings.shape[1])), dtype=np.float32)
    test_generator.reset_pointer()

    if read_as_pickle:
        test_set_size = len(test_generator.pickled_labels)
    else:
        # TODO: fix so that test frames can be written directly
        # # Embeddings learned for test set
        # According to ../split_dataset_with_labels_world.py
        test = []
        traj = 1
        frames_total = 300
        for frame_id in range(frames_total):
            if frame_id % 5 == 3:
                test.append(frame_id)
                continue
        test_set_size = 0
        with open(test_files) as f:
            for i, l in enumerate(f):
                pass
            test_set_size = i + 1

    print("Test set has {} lines ".format(test_set_size))

    # Obtain embeddings for lines test set

    # NOTE: Pickle files might store lines images in a different 'order' than
    # the one corresponding to the list of images in the text file. This means
    # that the method that obtains the batches provides lines in different order
    # if executed in read_as_pickle mode or not. Therefore, the embeddings
    # obtained in the two cases will not be comparable, since, i.e., the first
    # embedding will correspond to a certain line in the read_as_pickle mode and
    # to another one in the text-files mode. Also, when the number of lines in
    # the test set is not a multiple of the batch size, for some lines the
    # embeddings will not be obtained. These lines without embeddings will be
    # different in the two reading modes for the reasons explained above and
    # therefore some lines might be visualized in one case but not in the other.

    #test_loss = 0.
    #test_count = 0

    for i in range(test_set_size / batch_size):
        batch_x, batch_labels = test_generator.next_batch(batch_size)

        # Pickled files have labels in the endpoints format -> convert them
        # to center format
        if read_as_pickle:
            batch_labels = get_line_center(batch_labels)

        output = sess.run(
            embeddings,
            feed_dict={
                x: batch_x,
                labels: batch_labels,
                keep_prob: 1.
            })
        #current_test_loss = sess.run(
        #    triplet_loss, feed_dict={
        #        x: batch_x,
        #        labels: batch_labels,
        #        keep_prob: 1.
        #    })
        #test_loss += current_test_loss
        #test_count += 1

        test_embeddings_all = np.vstack([test_embeddings_all, output])
        # Display every 5 steps
        if i % 5 == 0:
            print("Embeddings got for {} lines ".format(
                test_embeddings_all.shape[0]))

    lines_total = test_embeddings_all.shape[0]
    print("In total, embeddings got for {} lines ".format(lines_total))
    #average_test_loss = test_loss / test_count
    #print("{} Average loss for test set = {:.4f}".format(
    #    datetime.now(), average_test_loss))

    print("Writing embeddings to file")
    np.save(embeddings_path, test_embeddings_all)

number_of_lines_with_embeddings = len(test_embeddings_all)

# Retrieve true instances
if read_as_pickle:
    data_lines_world = np.array(test_generator.pickled_labels, dtype=np.float32)
    print('Shape of data_lines_world is {}'.format(data_lines_world.shape))
else:
    from tools.visualization import get_lines_world_coordinates_with_instances
    data_lines_world = get_lines_world_coordinates_with_instances(
        trajectory=traj, frames=test, dataset_name='train')

# Only keep the lines for which an embedding was seeked (since data is processed
# in batches only for a number of lines multiple of the batch size the embedding
# is computed, cf. above)
data_lines_world = data_lines_world[:number_of_lines_with_embeddings]
instance_labels = data_lines_world[:, -1]

# Instances obtained via K-means clustering on obtained embeddings
from sklearn.cluster import KMeans

lines_features = test_embeddings_all
n_clusters = 12
#n_clusters = int(max(instance_labels))
kmeans = KMeans(n_clusters, init='k-means++').fit(lines_features)
cluster_labels = kmeans.labels_
#count = cluster_labels.shape[0]

# To display frequencies
count_map_cluster_labels_to_instance_labels = np.zeros(
    [max(cluster_labels) + 1,
     int(max(instance_labels)) + 1])
for label_index in range(len(cluster_labels)):
    cluster_label = cluster_labels[label_index]
    corresponding_instance_label = int(instance_labels[label_index])
    count_map_cluster_labels_to_instance_labels[
        cluster_label, corresponding_instance_label] += 1

# Map real instances and instances from clustering
from tools.visualization import pcl_lines_for_plot

pcl_lines_open3d_cluster = pcl_lines_for_plot(
    data_lines_world, lines_color=cluster_labels, visualizer='open3d')
pcl_lines_open3d_ground_truth = pcl_lines_for_plot(
    data_lines_world,
    lines_color=np.int32(instance_labels),
    visualizer='open3d')
pcl_lines_matplotlib_cluster = pcl_lines_for_plot(
    data_lines_world, lines_color=cluster_labels, visualizer='matplotlib')
pcl_lines_matplotlib_ground_truth = pcl_lines_for_plot(
    data_lines_world,
    lines_color=np.int32(instance_labels),
    visualizer='matplotlib')

from tools.visualization import plot_lines_with_open3d
#from tools.visualization import plot_lines_with_matplotlib

print("Displaying scene with obtained instances")
plot_lines_with_open3d(pcl_lines_open3d_cluster, "Clusterized instances")
#plot_lines_with_matplotlib(pcl_lines_matplotlib_cluster)
print("Displaying scene with ground-truth instances")
plot_lines_with_open3d(pcl_lines_open3d_ground_truth, "Ground-truth instances")
#plot_lines_with_matplotlib(pcl_lines_matplotlib_ground_truth)


# # See embeddings in the feature space, colored with instance label
from tensorflow.contrib.tensorboard.plugins import projector
LOG_DIR = os.path.join(log_files_folder, 'embedding_logs')
if not os.path.isdir(LOG_DIR): os.makedirs(LOG_DIR)
metadata = os.path.join(LOG_DIR, 'embedding_metadata.tsv')
test_embeddings = tf.Variable(test_embeddings_all, name='test_embeddings')

with open(metadata, 'w') as metadata_file:
    for label in instance_labels:
        metadata_file.write('%d\n' % label)

with tf.Session() as sess:
    saver = tf.train.Saver([test_embeddings])

    sess.run(test_embeddings.initializer)
    saver.save(sess, os.path.join(LOG_DIR, 'test_embeddings.ckpt'))

    config = projector.ProjectorConfig()
    # One can add multiple embeddings.
    embedding = config.embeddings.add()
    embedding.tensor_name = test_embeddings.name
    print('test_embeddings: {0}'.format(test_embeddings))
    # Link this tensor to its metadata file (e.g. labels).
    embedding.metadata_path = metadata
    # Saves a config file that TensorBoard will read during startup.
    projector.visualize_embeddings(tf.summary.FileWriter(LOG_DIR), config)

#include <ros/console.h>
#include <ros/ros.h>

#include <line_detection/line_detection.h>
#include <pcl/conversions.h>
#include <pcl/visualization/cloud_viewer.h>
#include <pcl/visualization/pcl_visualizer.h>
#include <pcl_ros/point_cloud.h>
#include <sensor_msgs/PointCloud2.h>

int main(int argc, char** argv) {
  // This lets DEBUG messages display on console
  if (ros::console::set_logger_level(ROSCONSOLE_DEFAULT_NAME,
                                     ros::console::levels::Debug)) {
    ros::console::notifyLoggerLevelsChanged();
  }
  ros::init(argc, argv, "test_point_cloud");
  ros::NodeHandle node_handle;

  // Load both depth and color image.
  cv::Mat depth;
  cv::Mat image;
  image = cv::imread("hall.jpg", CV_LOAD_IMAGE_COLOR);
  depth = cv::imread("hall_depth.png", CV_LOAD_IMAGE_UNCHANGED);
  if (!image.data) {
    ROS_INFO_STREAM(
        "Image could not be loaded. Please make shure to run the node in a "
        "directory that contains the image hall.jpg and the corresponding "
        "depth image hall_depth.png");
    return -1;
  }
  if (!depth.data) {
    ROS_INFO_STREAM(
        "Image could not be loaded. Please make shure to run the node in a "
        "directory that contains the image hall.jpg and the corresponding "
        "depth image hall_depth.png");
    return -1;
  }

  // Create a point cloud. The pointer is used to handle to the PCLVsualizer,
  // the reference is needed to handle to cloud to the computePointCloud
  // function.
  pcl::PointCloud<pcl::PointXYZRGB>::Ptr cloud_ptr(
      new pcl::PointCloud<pcl::PointXYZRGB>);
  pcl::PointCloud<pcl::PointXYZRGB>& cloud = *cloud_ptr;

  // Create the calibration matrix. The values are more or less arbitrary.
  cv::Mat K(3, 3, CV_32FC1);
  K.at<float>(0, 0) = 570.3f;
  K.at<float>(0, 1) = 0.0f;
  K.at<float>(0, 2) = 960.0f;
  K.at<float>(1, 0) = 0.0f;
  K.at<float>(1, 1) = 570.3f;
  K.at<float>(1, 2) = 540.0f;
  K.at<float>(2, 0) = 0.0f;
  K.at<float>(2, 1) = 0.0f;
  K.at<float>(2, 2) = 1.0f;

  // Compute the point cloud.
  line_detection::LineDetector line_detector;
  line_detector.computePointCloud(image, depth, K, cloud);

  // These mean values are used in the unit tests (copied there by hand). So to
  // make changes there later, this code should stay here
  double x_mean = 0;
  double y_mean = 0;
  double z_mean = 0;
  double r_mean = 0;
  double g_mean = 0;
  double b_mean = 0;
  for (int i = 0; i < cloud.size(); i++) {
    if (std::isnan(cloud.points[i].x)) continue;
    x_mean += cloud.points[i].x;
    y_mean += cloud.points[i].y;
    z_mean += cloud.points[i].z;
    r_mean += cloud.points[i].r;
    g_mean += cloud.points[i].g;
    b_mean += cloud.points[i].b;
  }
  x_mean = x_mean / cloud.size();
  y_mean = y_mean / cloud.size();
  z_mean = z_mean / cloud.size();
  r_mean = r_mean / cloud.size();
  g_mean = g_mean / cloud.size();
  b_mean = b_mean / cloud.size();
  ROS_DEBUG_STREAM("\n"
                   << "x_mean = " << x_mean << endl
                   << "y_mean = " << y_mean << endl
                   << "z_mean = " << z_mean << endl
                   << "r_mean = " << r_mean << endl
                   << "g_mean = " << g_mean << endl
                   << "b_mean = " << b_mean << endl);

  // Visualize it.
  pcl::visualization::PCLVisualizer viewer("3D Viewer");
  viewer.setBackgroundColor(1, 1, 1);
  viewer.addCoordinateSystem(1.0f, "global");
  viewer.addPointCloud(cloud_ptr, "original point cloud");
  viewer.spin();
  return 0;
}

#include <opencv2/highgui/highgui.hpp>
#define DATA_BUF_SIZE 200
#define ACC_THRESH 0.20
#define ACC_PLOT_HT 200
#define DIST_THRESH_M 100
#define BUF_SIZE 1000
#define PLOT_HT 200
#define TWO_SEC_WINDOW 2.3148148148148147e-05
#define FEATURE_VC_LN 5

#define PI 3.1415926535897932384626433832795
#define DEG2RAD(x) (x * PI / 180)

typedef struct _loc
{
	double lat;
	double lon;
}loc;

typedef struct sensor_
{
	double timestamp;
	double lat;
	double lon;
	double speed;
	double accX;
	double accY;
	double accZ;
	double accG;
	double Roll; 
	double Pitch; 
	double Yaw;
	double fileName;
}sensorData;

	typedef struct windowID_
	{
		int nthVec;
		int nthEle;
	}windowID;

	typedef struct mapNodes
	{
		loc node;
		float p_roadTex[3];
		float p_roadCon[3];
		windowID window[10];
		bool visited;
	}mapNode;

cv::Mat getRotationMatrix(double roll, double pitch, double yaw);
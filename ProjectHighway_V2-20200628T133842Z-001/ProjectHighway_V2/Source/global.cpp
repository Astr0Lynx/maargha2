#include "global.h"
using namespace cv;

Mat getRotationMatrix(double Rx, double Ry, double Rz)
{
	Mat rotMat;

	Mat rotMat1(3, 3, CV_32F, Scalar(0));
	rotMat1.at<float>(0,0) = 1;			rotMat1.at<float>(0,1) = 0;			rotMat1.at<float>(0,2) = 0;						
	rotMat1.at<float>(1,0) = 0;			rotMat1.at<float>(1,1) = cos(Rx);	rotMat1.at<float>(1,2) = -sin(Rx);	
	rotMat1.at<float>(2,0) = 0;			rotMat1.at<float>(2,1) = sin(Rx);	rotMat1.at<float>(2,2) =  cos(Rx);	

	Mat rotMat2(3, 3, CV_32F, Scalar(0));
	rotMat2.at<float>(0,0) = cos(Ry);	rotMat2.at<float>(0,1) = 0;			rotMat2.at<float>(0,2) = sin(Ry);						
	rotMat2.at<float>(1,0) = 0;			rotMat2.at<float>(1,1) = 1;			rotMat2.at<float>(1,2) = 0;						
	rotMat2.at<float>(2,0) = -sin(Ry);	rotMat2.at<float>(2,1) = 0;			rotMat2.at<float>(2,2) = cos(Ry);						
	

	Mat rotMat3(3, 3, CV_32F, Scalar(0));
	rotMat3.at<float>(0,0) = cos(Rz);	rotMat3.at<float>(0,1) = -sin(Rz);	rotMat3.at<float>(0,2) = 0;						
	rotMat3.at<float>(1,0) = sin(Rz);	rotMat3.at<float>(1,1) =  cos(Rz);	rotMat3.at<float>(1,2) = 0;						
	rotMat3.at<float>(2,0) = 0;			rotMat3.at<float>(2,1) = 0;			rotMat3.at<float>(2,2) = 1;						
	
	rotMat = rotMat3*rotMat2*rotMat1;

	return rotMat;
}

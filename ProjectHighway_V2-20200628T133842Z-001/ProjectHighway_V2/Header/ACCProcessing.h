#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/calib3d.hpp>
#include <process.h>
#include <iostream>
#include <fstream>
#include <Windows.h>
#include <string>
#include <stdio.h>

using namespace std;
using namespace cv;

class ACCProcessing
{
private:
	
	
public:
	ACCProcessing();
	virtual ~ACCProcessing();	
	void processACC(Mat *accPlot);
	void train(void);
	void classify(double lat, double lon);
	float CalculateEuclidean(vector<float> vec1,vector<float> vec2);
};
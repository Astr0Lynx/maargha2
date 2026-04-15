// GPSInfo.h: interface for the GPSInfo class.
//
//////////////////////////////////////////////////////////////////////
#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/calib3d.hpp>
#include <process.h>
#include <iostream>
#include <fstream>
#include <boost/date_time/posix_time/posix_time.hpp>
#include <Windows.h>
#include <stdio.h>
#include "global.h"
using namespace std;
using namespace cv;



class GPSProcessing
{
private:
	Point2d tngtPlaneProj(loc mapCenter,loc ltlnPt);
	void latlon2Cart_mlti_pt(vector <loc> *wayPts,vector <vector<loc>> *wayGrp,vector <Point2f> *cartWayPts,vector <vector<Point2f>> *cartWayPtsGrp,loc mapCenter);
	Point2d latlon2Cart_1_pt(loc ltlnPt,loc mapCenter);
	void mapRead(vector <loc> *wayPts,vector <vector<loc>> *wayPtsGrp);
	void gpsMapRecenter(vector <vector<Point2f>> *tngtPrjwayGrp,Mat image);
public:
	GPSProcessing();
	virtual ~GPSProcessing();
	void drawGPSMap(loc mapCenter,bool *readMapFlag,Mat mapImage,vector <loc> *wayPts,vector <vector<loc>> *wayGrp);
	void findViewCircle(loc mapCenter, loc myLoc,vector <loc> *wayPts,vector <vector<loc>> *wayGrp,vector <vector<loc>> *subWayPtsGrp,double azimuth,Mat *viewCircle);
	void mapMatching(loc mapCenter,vector <loc> *wayPt,vector <vector<loc>> *wayGrp,double azimuth);
};


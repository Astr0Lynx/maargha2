// GPSInfo.cpp: implementation of the GPSInfo class.
//
//////////////////////////////////////////////////////////////////////
#include "../Header/GPSProcessing.h"
#include <deque>

//Global Variables
static bool switchOFF;
extern std::deque<loc>gpsTrack;
loc lastPOS;	
loc corGPSPt;
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

GPSProcessing::GPSProcessing()
{}

GPSProcessing::~GPSProcessing()
{}


Point2d GPSProcessing::tngtPlaneProj(loc mapCenter,loc ltlnPt)
{
	Point2d tmploc;
    tmploc.x = 51500 * (-mapCenter.lon +ltlnPt.lon);
	tmploc.y = 51500 * (mapCenter.lat -ltlnPt.lat);//assume earth is flat in the small FOV. the difference is multiplied with scale factor..
	//the above formula will work only in the northern hemisphere and east of meridian
	return tmploc;
}
double gpsDistance1(loc presPOS, loc prevPOS) 
{
	if((presPOS.lat == prevPOS.lat) && (presPOS.lon == prevPOS.lon))
		return 0;
    double earthRadius = 6371; //kilometers
	double dLat = DEG2RAD((prevPOS.lat-presPOS.lat));
    double dLng = DEG2RAD((prevPOS.lon-presPOS.lon));
    double a = sin(dLat/2) * sin(dLat/2) +
               cos(DEG2RAD(presPOS.lat)) * cos(DEG2RAD(prevPOS.lat)) *
               sin(dLng/2) * sin(dLng/2);
    double c = 2 * atan2(sqrt(a), sqrt(1-a));
    double dist = (earthRadius * c);
    return dist*1000;
}


void GPSProcessing::latlon2Cart_mlti_pt(vector <loc> *wayPts,vector <vector<loc>> *wayGrp,vector <Point2f> *cartWayPts,vector <vector<Point2f>> *cartWayPtsGrp,loc mapCenter)
{
	Point2f cartWayPt;
	for(unsigned int i =0; i < wayGrp->size(); i++)
	{
		for(unsigned int j = 0; j< wayGrp->at(i).size(); j++)
		{
			double d = gpsDistance1(mapCenter,wayGrp->at(i).at(j));
			if(d>1000.0)//only points within 1 km radius is drawn on the map
				continue;
			cartWayPt = tngtPlaneProj(mapCenter,wayGrp->at(i).at(j));
			cartWayPts->push_back(cartWayPt);
		}
		if(!cartWayPts->empty())
			cartWayPtsGrp->push_back(*cartWayPts);
		cartWayPts->clear();
	}
}

Point2d GPSProcessing::latlon2Cart_1_pt(loc ltlnPt,loc mapCenter)
{
	Point2d tmploc;
    tmploc.x = 51500 * (-mapCenter.lon +ltlnPt.lon);
	tmploc.y = 51500 * (mapCenter.lat -ltlnPt.lat);//assume earth is flat in the small FOV. the difference is multiplied with scale factor..
	//the above formula will work only in the northern hemisphere and east of meridian
	return tmploc;
}


void GPSProcessing::mapRead(vector <loc> *wayPts,vector <vector<loc>> *wayPtsGrp)
{
	loc tmpLoc;
	FILE *fp;
	fp = fopen("nodeLatLon2.txt","r");
	while(fscanf(fp,"%lf %lf\n",&tmpLoc.lat,&tmpLoc.lon) == 2)
	{
		if((tmpLoc.lat < 999.99) && (tmpLoc.lon < 999.99))
			wayPts->push_back(tmpLoc);
		else
		{
			wayPtsGrp->push_back(*wayPts);
			wayPts->clear();
		}
	}
	fclose(fp);
}



/*
void GPSProcessing::networkMap(vector <loc> *wayPts,vector <vector<loc>> *wayPtsGrp, vector<mapNode> *mapNodes,vector<vector<mapNode>> *mapNetwork)
{
	wayPts->clear();
	mapNode nodePt;
	//traverse through the geoPts and find the junctions, connect the junctions
	for(int i=0;wayPtsGrp->size();i++)
	{
		wayPts = wayPtsGrp->at(i);
		for(int j=0;wayPts->size();j++)
		{
			nodePt.node.lat = wayPts->at(j).lat;
			nodePt.node.lon = wayPts->at(j).lon;
			nodePt.p_roadCon[0]=1/3;nodePt.p_roadCon[1]=1/3;nodePt.p_roadCon[2]=1/3;
			nodePt.p_roadTex[0]=1/3;nodePt.p_roadTex[1]=1/3;nodePt.p_roadTex[2]=1/3;

			isJunction(wayPtsGrp,loc(wayPts->at(j).lat,wayPts->at(j).lon));

			mapNodes->push_back()
		}
	}
}
*/


void GPSProcessing::gpsMapRecenter(vector <vector<Point2f>> *tngtPrjwayGrp,Mat image)
{

	Mat offset(3, 3, CV_32F, Scalar(0));
	vector<cv::Point2f>tmpTrnwayPts;     
	vector <vector<Point2f>> tmpTrnwayGrp;

	//offset matrix. This is to transform the negative points to positive
	offset.at<float>(0,0) = 1;
	offset.at<float>(1,1) = 1;
	offset.at<float>(2,2) = 1;
	offset.at<float>(0,2) = image.cols/2;
	offset.at<float>(1,2) = image.rows/2;
 
	for(int i =0; i < tngtPrjwayGrp->size(); i++)
	{
		tmpTrnwayPts.clear();   
		cv::perspectiveTransform(tngtPrjwayGrp->at(i),tmpTrnwayPts,offset);
		tmpTrnwayGrp.push_back(tmpTrnwayPts);
	}

	image.setTo(cv::Scalar(0,0,0));
	for (int i=0;i<tmpTrnwayGrp.size();i++)
	{
		tmpTrnwayPts.clear();
		tmpTrnwayPts = tmpTrnwayGrp.at(i);
  		for (int j=0;j<(tmpTrnwayPts.size()-1);j++)
		{
			line(image,tmpTrnwayPts.at(j),tmpTrnwayPts.at(j+1),Scalar(255,255,255),2,8,0);
			circle(image,tmpTrnwayPts.at(j+1),2,Scalar(0,255,0),-1,8,0);
		//	namedWindow("gpsMap");
		//	imshow("gpsMap",image);
		}	
		//waitKey(0);

	} 
	circle(image,Point2f(image.cols/2,image.rows/2),2,Scalar(0,0,255),-1,8,0);
}



void GPSProcessing::drawGPSMap(loc mapCenter,bool *readMapFlag,Mat mapImage,vector <loc> *wayPts,vector <vector<loc>> *wayGrp)
{
	vector <Point2f> cartWayPts;
	vector <vector<Point2f>> cartWayPtsGrp;
	Point2f cartLastPOS;
	Point2f pt1,pt2;
	
	if(*readMapFlag == true)//this is to read the map for the first time
	{	
		wayPts->clear();
		wayGrp->clear();
		mapRead(wayPts,wayGrp);
		*readMapFlag = false;
		//networkMap(wayGrp,);
	}
	else
	{
		cartWayPts.clear();
		cartWayPtsGrp.clear();
		latlon2Cart_mlti_pt(wayPts,wayGrp,&cartWayPts,&cartWayPtsGrp,mapCenter);
		//the tangent plane has points with mapCenter at he origin (0,0)
		//so it has to be brought to the center of the image
		gpsMapRecenter(&cartWayPtsGrp,mapImage);
		//draw the last point
		cartLastPOS = latlon2Cart_1_pt(lastPOS,mapCenter);
		//drawing the gps trajectory that the car travels
		for(unsigned int i=0;i!=gpsTrack.size()-1;i++)
		{
			if((gpsTrack.at(i).lat!=gpsTrack.at(i+1).lat)&&(gpsTrack.at(i).lon!=gpsTrack.at(i+1).lon)
				&&(gpsTrack.at(i).lat!=0)&&(gpsTrack.at(i).lon!=0)
				&&(gpsTrack.at(i+1).lat!=0)&&(gpsTrack.at(i+1).lon!=0))
			{
				pt1=latlon2Cart_1_pt(gpsTrack.at(i),mapCenter);
				pt2=latlon2Cart_1_pt(gpsTrack.at(i+1),mapCenter);
				pt1.x = pt1.x+ mapImage.cols/2;
				pt1.y = pt1.y+ mapImage.rows/2;
				pt2.x = pt2.x+ mapImage.cols/2;
				pt2.y = pt2.y+ mapImage.rows/2;
				cv::line(mapImage,pt1,pt2,Scalar(255,0,255),2,8,0);
			}
		}


		//center pixel (myLoc)
		circle(mapImage,Point2f(cartLastPOS.x+mapImage.cols/2,cartLastPOS.y+mapImage.rows/2),4,Scalar(255,0,255),1,8,0);

		namedWindow("gpsMap");
		imshow("gpsMap",mapImage);
		
	}
}



//----------------------------------------------------------------------
float diffSlope(float slope1,float slope2)
{
	if(abs(slope1-slope2)>180)
		return abs((abs(slope1-slope2)-360));
	else
		return abs(slope1-slope2);
}

float addSlope(float slope1,float slope2)
{
	if(abs(slope1+slope2)>360)
		return ((slope1+slope2)-360);
	else
		return (slope1+slope2);
}
float findSlope(Point2f pt1,Point2f pt2)
{
	float slopeAngle = 0;
	float deltaY = pt2.y - pt1.y;
	float deltaX = pt2.x - pt1.x;

	if(deltaX!=0)
		slopeAngle = (atan2(deltaY, deltaX) * (180 / PI))+180;
	else if(deltaY > 0)
		slopeAngle = 90;
	else
		slopeAngle = 270;

	return slopeAngle;
}

float CalculateDistance(Point2f pt1,Point2f pt2)
{
	float distance;
	
	//Euclidean distance
	distance = pow((pow((double)(pt1.x - pt2.x), 2.0) + pow((double)(pt1.y - pt2.y), 2.0)),(0.5));//change to increase the dimension

	return distance;

}

void FOV_Recenter(vector <vector<Point2f>> *tngtPrjwayGrp,Mat* image,bool SINGLE_PT)
{

	Mat offset(3, 3, CV_32F, Scalar(0));
	vector<cv::Point2f>tmpTrnwayPts;     
	vector <vector<Point2f>> tmpTrnwayGrp;

	//offset matrix. This is to transform the negative points to positive
	offset.at<float>(0,0) = 1;
	offset.at<float>(1,1) = 1;
	offset.at<float>(2,2) = 1;
	offset.at<float>(0,2) = image->cols/2;
	offset.at<float>(1,2) = image->rows/2;
 
	for(int i =0; i < tngtPrjwayGrp->size(); i++)
	{
		tmpTrnwayPts.clear();   
		cv::perspectiveTransform(tngtPrjwayGrp->at(i),tmpTrnwayPts,offset);
		tmpTrnwayGrp.push_back(tmpTrnwayPts);
	}

	if(!SINGLE_PT)
	{
		image->setTo(cv::Scalar(0,0,0));
		for (int i=0;i<tmpTrnwayGrp.size();i++)
		{
			tmpTrnwayPts.clear();
			tmpTrnwayPts = tmpTrnwayGrp.at(i);
  			for (int j=0;j<(tmpTrnwayPts.size()-1);j++)
			{
				line(*image,tmpTrnwayPts.at(j),tmpTrnwayPts.at(j+1),Scalar(255,255,255),2,8,0);
			}	
		} 
		circle(*image,Point2f(image->cols/2,image->rows/2),2,Scalar(0,0,255),-1,8,0);
	}
	else
		//already image exists . we are only updating the single point on the screen
	{
		circle(*image,tmpTrnwayPts.at(0),2,Scalar(255,255,0),-1,8,0);
		line(*image,tmpTrnwayPts.at(1),tmpTrnwayPts.at(2),Scalar(255,255,0),2,8,0);
	}
	namedWindow("FOV");
	imshow("FOV",*image);

}

void lineEqnCoeff(Point2f *Pt1,Point2f *Pt2,float *a,float *b,float *c)
{
	//line eqn coefficients
	*a =  (Pt2->y-Pt1->y);
	*b = -(Pt2->x-Pt1->x);
	*c =  (Pt2->x*Pt1->y - Pt2->y*Pt1->x);
}
//----------------------------------------------------------------------
void GPSProcessing:: findViewCircle(loc mapCenter, loc myLoc,vector <loc> *wayPts,vector <vector<loc>> *wayGrp,vector <vector<loc>> *subWayPtsGrp,double azimuth, Mat *viewCircle)
{
	vector <loc> subWayPts;
	
	subWayPtsGrp->clear();
	float viewDist;

	vector <Point2f> cartWayPts;vector <vector<Point2f>> cartWayGrp;
	viewDist = CalculateDistance(Point2f(mapCenter.lon,mapCenter.lat),Point2f(myLoc.lon,myLoc.lat));
	loc tmpLoc1;
	loc tmpLoc2;

	//works for northern hemisphere
	for (unsigned int i=0;i<wayGrp->size();i++)
	{
		for(unsigned int j = 0; j< wayGrp->at(i).size()-1; j++)
		{
			tmpLoc1 = wayGrp->at(i).at(j);
			tmpLoc2 = wayGrp->at(i).at(j+1);

			if(  ((tmpLoc1.lat > (mapCenter.lat + viewDist)) && ((tmpLoc2.lat > (mapCenter.lat + viewDist))))  //above
			   ||((tmpLoc1.lat < (mapCenter.lat - viewDist)) && ((tmpLoc2.lat < (mapCenter.lat - viewDist))))  //below
			   ||((tmpLoc1.lon > (mapCenter.lon + viewDist)) && ((tmpLoc2.lon > (mapCenter.lon + viewDist))))  //left
			   ||((tmpLoc1.lon < (mapCenter.lon - viewDist)) && ((tmpLoc2.lon < (mapCenter.lon - viewDist))))) //right
				continue;//skip those points
			else
			{
				subWayPts.push_back(wayGrp->at(i).at(j));
				subWayPts.push_back(wayGrp->at(i).at(j+1));
			}
		}
		if(!subWayPts.empty())
			subWayPtsGrp->push_back(subWayPts);
		subWayPts.clear();
	}
	latlon2Cart_mlti_pt(&subWayPts,subWayPtsGrp,&cartWayPts,&cartWayGrp,mapCenter);

	FOV_Recenter(&cartWayGrp,viewCircle,false);
	waitKey(1);
}


void GPSProcessing::mapMatching(loc rawGPSPt,vector <loc> *wayPt,vector <vector<loc>> *wayGrp,double azimuth)
{ 
	//select sub set of the network around the point--------
	vector <vector<loc>> subWayPtsGrp;
	vector <Point2f> cartWayPts_;vector <vector<Point2f>> cartWayGrp_;
	vector <loc> subWayPts;
	Point2f selP;
	Point2f selPt1;
	Point2f selPt2;
	float a,b,c;
	Point2f P;
	float linePtDist;
	//clear every time to start fresh vector
	subWayPtsGrp.clear();
	subWayPts.clear();
	//a circle of 1 km
	loc fovRadiusGPS;fovRadiusGPS.lat=0.0015;fovRadiusGPS.lon=0.0015;
	loc fov;
	//works for north eastern hemisphere
	fov.lat = rawGPSPt.lat+fovRadiusGPS.lat;
	fov.lon = rawGPSPt.lon+fovRadiusGPS.lon;
	cv::Mat viewCircle(500,500,CV_32FC3,cv::Scalar(0));
	findViewCircle(rawGPSPt, fov ,wayPt,wayGrp,&subWayPtsGrp,azimuth,&viewCircle);
	
	//actual map matching-----------------------------------
	//GPS point is the center of the map
	Point2f Pt(0,0);
	//find the segments that are of same slope and find their points related to our GPS pt
	vector<double> shortestDist;
	vector<Point2f> point;
	float shortDist = 9999;
	for(unsigned int i=0;i<subWayPtsGrp.size();i++)
	{
		subWayPts.clear();
		subWayPts = subWayPtsGrp.at(i); 
		for(unsigned int j=0;j<subWayPts.size()-1;j++)
		{
			//for every line segment calculate the shortest distance
			Point2f pt1=latlon2Cart_1_pt(subWayPts.at(j),rawGPSPt);
			Point2f pt2=latlon2Cart_1_pt(subWayPts.at(j+1),rawGPSPt);
			//to find closest point on the line ax+by+c=0 we need its coefficients
			lineEqnCoeff(&pt1,&pt2,&a,&b,&c);

			//projection point P given an equation and point
			P.x = (b*( b*Pt.x-a*Pt.y)-a*c)/(a*a+b*b);
			P.y = (a*(-b*Pt.x+a*Pt.y)-b*c)/(a*a+b*b);

			//AC slope and CB slope must be same or approximately same
			float slopeAC = findSlope(pt1,P);
			float slopeCB = findSlope(P,pt2);

			if(diffSlope(slopeAC,slopeCB)>20)
				continue;

			//find the shortest distance between the point and line. Take the point that is closest
			linePtDist = abs(a*Pt.x+b*Pt.y+c)/sqrt(a*a+b*b);

			if(shortDist>linePtDist)
			{
				shortDist = linePtDist;
				selP.x = P.x;selP.y = P.y;
				selPt1.x = pt1.x; selPt1.y = pt1.y;
				selPt2.x = pt2.x; selPt2.y = pt2.y;
			}
			else
				continue;
		}
	}
		//draw the point for debug
		cartWayPts_.clear();
		cartWayGrp_.clear();
		cartWayPts_.push_back(selP);//just to make P fit the input parameter data type
		cartWayPts_.push_back(selPt1);
		cartWayPts_.push_back(selPt2);
		cartWayGrp_.push_back(cartWayPts_);
		FOV_Recenter(&cartWayGrp_,&viewCircle,true);
		waitKey(1);	

	//Convert the point back to GPS coordinate
    corGPSPt.lon = (selP.x/51500) + rawGPSPt.lon;
	corGPSPt.lat = rawGPSPt.lat - (selP.y/51500);//assume earth is flat in the small FOV. the difference is multiplied with scale factor..
	//the above formula will work only in the northern hemisphere and east of meridian


}


/*
void GPSProcessing::startGPS(void* param)
{
	
	switchOFF = false;
	int idx=0;
	string line1 = "";
	string line2 = "";
	const char* c_line;
	double tmp1 = 0;
	double m_lat = 0;
	double m_lon = 0;
	double m_time1 = 0;
	double m_time2 = 0;
	double delay;
	loc myLoc;
	vector <loc> wayPts;vector <vector<loc>> wayPtsGrp;
	bool readMapFlag = true;
	cv::Mat gpsMap(300,300,CV_32FC3,cv::Scalar(0));

	ifstream gpsLatFile("Data//ANDGPSLA2014-10-30-09-42-24.csv");
	ifstream gpsLonFile("Data//ANDGPSLO2014-10-30-09-42-24.csv");
	
	//read the initial sensor timestamp--------------------
	if(!getline(gpsLatFile, line1))
		_endthread();
	else
	{
		c_line =line1.c_str();
		sscanf_s(c_line,"%lf,%lf,%lf",&tmp1,&m_time1,&m_lat);
	}

	if(!getline(gpsLonFile, line2))
		_endthread();
	else
	{
		c_line =line2.c_str();
		sscanf_s(c_line,"%lf,%lf,%lf",&tmp1,&m_time1,&m_lon);
	}
	//------------------------------------------------------
	time_t t = std::time(0);
	g_timestamp = 0.404490310;
	double milliseconds;
	boost::posix_time::ptime now = boost::posix_time::microsec_clock::local_time();
	boost::posix_time::time_duration td = now.time_of_day();
	milliseconds=(td.total_milliseconds())/86400000.0;
	double timestamp_offset = milliseconds - g_timestamp;
	

	while(getline(gpsLatFile, line1) && (getline(gpsLonFile, line2)))
	{
		//read the GPS data
		c_line =line1.c_str();
		sscanf_s(c_line,"%lf,%lf,%lf",&tmp1,&m_time2,&m_lat);
		c_line =line2.c_str();
		sscanf_s(c_line,"%lf,%lf,%lf",&tmp1,&m_time2,&m_lon);

		//sync
		
		while(g_timestamp<m_time2)
		{
			now = boost::posix_time::microsec_clock::local_time();
			td = now.time_of_day();
			g_timestamp = ((td.total_milliseconds())/86400000.0)-timestamp_offset;
		}

		cout <<m_time2<<" "<<g_timestamp<<" "<<CAMtimestamp<< endl;
		//delay is calculated as per the timestamp
		delay = (m_time2-m_time1)*86400000;
		//cout << delay <<endl;
		myLoc.lat = m_lat;
		myLoc.lon = m_lon;
		//mapMatch();
		//drawGPSMap(myLoc,&readMapFlag,gpsMap,&wayPts,&wayPtsGrp);
		//Sleep(delay); //wait in milli seconds
		waitKey(1);
		m_time1 = m_time2;
		if(switchOFF)
			break;
	}
	_endthread();
}
	

void GPSProcessing::beginGPSProcessing()
{
	void* param=0;
	_beginthread(startGPS,0,param);
}

void GPSProcessing::stopGPSProcessing()
{
	switchOFF = true;
}
*/

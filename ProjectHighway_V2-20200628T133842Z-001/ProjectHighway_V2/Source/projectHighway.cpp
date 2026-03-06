#include <iostream>
#include <fstream>
#include <math.h> 
#include "Serial.h"
#include <process.h>
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/calib3d/calib3d.hpp>
#include "ACCProcessing.h"
#include "GPSProcessing.h"
#include "CAMProcessing.h"
//#include "TIMThread.h"


using namespace cv;
using namespace std;

#define CAMERA_ONLY
#define SENSOR_ONLY
//Generic Macros
#define PI 3.1415926535897932384626433832795
#define DEG2RAD(x) (x * PI / 180)
#define RAD2DEG(x) (x * 180 / PI)


//Global Data

double timestamp;
static bool switchOFF;
sensorData prevData;
sensorData liveData;
string roadTexture;
int roadCondition;
Mat camPIC;
Mat camPIC_copy;
bool TRAIN=false;
bool CLASSIFY= false;
bool NewFile=false;
bool NewGPS=false;
extern int BOX_Ox;
extern int BOX_Oy;
extern int BOX_W;
extern int BOX_H;
bool boxPresent=false;
string imgName="";
vector <vector <float>> trainingDataSet;
vector <float> trainingDataElement;
double RMSDX;
double RMSDY;
double RMSDZ;
//------------------
string roadSurfaceResult;
string roadConditionResult;
extern loc corGPSPt;
//------------------
void get_sensor_data(string* line,ifstream* dataFile,Serial *comObj)
{
	//declarations
	double factor = 0.5;
	char serialData[50];
	static double Actual_prevDataAccZ=0;
	static double Actual_prevDataAccX=0;
	//read data
	if(getline(*dataFile,*line))
	{
		const char* c_line =line->c_str();
		sscanf_s(c_line,"%lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf %lf",
						&liveData.timestamp,&liveData.accX,&liveData.accY,&liveData.accZ,
						&liveData.lat,&liveData.lon,&liveData.speed,
						&liveData.Yaw,&liveData.Roll,&liveData.Pitch,&liveData.fileName);

/*		sscanf_s(c_line,"%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf",
						&liveData.timestamp,&liveData.accX,&liveData.accY,&liveData.accZ,
						&liveData.lat,&liveData.lon,&liveData.speed,
						&liveData.Yaw,&liveData.Roll,&liveData.Pitch,&liveData.fileName);
*/
		//low pass filtering of attitude data
		liveData.Pitch	= liveData.Pitch*factor + prevData.Pitch*(1 - factor);
		liveData.Roll	= liveData.Roll*factor + prevData.Roll*(1 - factor);
		liveData.Yaw	= liveData.Yaw*factor + prevData.Yaw*(1 - factor);

		//high pmyass filter to filter out the sustained accelerations during vehicle turning and vehcile forward acceleration
		//0.85 is the factor for high pass filter
		double filteredAccZ = 0.85 * (prevData.accZ + liveData.accZ - Actual_prevDataAccZ);
		Actual_prevDataAccZ = liveData.accZ;
		liveData.accZ = filteredAccZ;
		double filteredAccX = 0.85 * (prevData.accX + liveData.accX - Actual_prevDataAccX);
		Actual_prevDataAccX = liveData.accX;
		liveData.accX = filteredAccX;

		sprintf(serialData,"%.2f,%.2f,%.2f\r\n",liveData.Pitch-40,liveData.Roll+20,0.0);
		comObj->writeData(serialData);

		//-Not used any more----------------------------------------------------------------
		//Now I am going to use a sensor app which gives gravity compensated acc values at a 
		//freq of 50 Hz against 15 Hz what I had previously.
		//find the gravity compensated accelerometer
		//assume phone is held vertically. Pitch zero, Roll zero
		//rotMat = getRotationMatrix(DEG2RAD(0),DEG2RAD(-liveData.Roll),DEG2RAD(0));
		//rotate the gravity vector to the phone's orientation
		//AccMat.at<float>(0,0)=liveData.accX;
		//AccMat.at<float>(1,0)=liveData.accY;
		//AccMat.at<float>(2,0)=liveData.accZ;
		//Also accG is not used any more, instead all the three axes are being used in feature vector
		//AccMat = (rotMat*AccMat)-gravity;
		//liveData.accG = AccMat.at<float>(2,0);
		//liveData.accG = liveData.accY-9.8;//debug
		//----------------------------------------------------------------------------------
	}
}

void dis_sensor_data(GPSProcessing *gpsDataPrs,ACCProcessing *accDataPrs,CAMProcessing *camDataPrs,bool* readMapflag,Mat *gpsMap,
					 vector<loc>*wayPt,vector<vector<loc>>*wayGrp,Mat* accPlot,vector<mapNode> *mapNodes,vector<vector<mapNode>> *mapNetwork)
{
	loc myLoc;
	
	if((prevData.accX != liveData.accX) ||
	   (prevData.accY != liveData.accY) ||
	   (prevData.accZ != liveData.accZ))
	{
		//cout<<"accelerometer"<<liveData.accX<<" "<<liveData.accY<<" "<<liveData.accZ<<endl;
		accDataPrs->processACC(accPlot);
		prevData.accX = liveData.accX;
		prevData.accY = liveData.accY;
		prevData.accZ = liveData.accZ;
		prevData.accG = liveData.accG;
	}

	if((prevData.lat != liveData.lat) ||
	   (prevData.lon != liveData.lon))
	{
		NewGPS = true;
		//next time we will know if the data is stale or fresh
		prevData.lat = liveData.lat;
		prevData.lon = liveData.lon;
		//map matching to choose the current lat,lon
		myLoc.lat = liveData.lat;
		myLoc.lon = liveData.lon;
		if(!*readMapflag)
			gpsDataPrs->mapMatching(myLoc,wayPt,wayGrp,liveData.Yaw);
		//draw GPS map with the latest data
		gpsDataPrs->drawGPSMap(myLoc,readMapflag,*gpsMap,wayPt,wayGrp);

		//gpsDataPrs->networkMap(wayPt,wayGrp,mapNodes,mapNetwork);
	}

	if((prevData.fileName!=liveData.fileName))//||(!boxPresent))
	{
		//readimage
		stringstream convert;
		convert << liveData.fileName;
		imgName = "Data//IMG_" + convert.str()+".jpg";
		camPIC = cv::imread(imgName,1);

		//cv::resize(camPIC,camPIC,cv::Size(camPIC.cols/6,camPIC.rows/6));
		//cv::transpose(camPIC,camPIC);

		camPIC.copyTo(camPIC_copy);
		//camPIC_copy = cv::imread(imgName,1);
		
		cv::rectangle(camPIC,cv::Point2f(BOX_Ox,BOX_Oy),cv::Point(BOX_Ox+BOX_W,BOX_Oy+BOX_H),Scalar(255,0,0),1,8,0);
		namedWindow("camPIC");
		imshow("camPIC",camPIC);
		if(!boxPresent)
			cv::waitKey(0);
		prevData.fileName=liveData.fileName;
		NewFile = true;
	}
	

	//testing purpose... copy should per individual sensors
//	memcpy(&prevData,&liveData,sizeof(sensorData));
}

void chooseBox( int event, int x, int y, int flags, void* param )
{	
	switch( event ){
		case CV_EVENT_MOUSEMOVE: 
			break;
		case CV_EVENT_LBUTTONDOWN:
			break;
		case CV_EVENT_LBUTTONUP:
			//start point
			BOX_Ox = x;
			BOX_Oy = y;
			boxPresent=true;
			//camPIC = cv::imread(imgName,1);
			cv::rectangle(camPIC,cv::Point2f(BOX_Ox,BOX_Oy),cv::Point(BOX_Ox+BOX_W,BOX_Oy+BOX_H),Scalar(255,0,0),1,8,0);
			namedWindow("camPIC");
			imshow("camPIC",camPIC);
			break;
		case CV_EVENT_RBUTTONDOWN:
			break;
		case CV_EVENT_RBUTTONUP:
			//update the box
			//boxPresent = true;
			break;
		case CV_EVENT_MBUTTONDOWN:
			break;
		case CV_EVENT_MBUTTONUP:
			break;
		default:
			break;
	}
}


void tarmudcon( int event, int x, int y, int flags, void* param )
{	
	switch( event ){
		case CV_EVENT_MOUSEMOVE: 
			break;
		case CV_EVENT_LBUTTONDOWN:
			//start recording
			TRAIN = true;
			roadTexture = "tar";// Tar Road
			break;
		case CV_EVENT_LBUTTONUP:
			CLASSIFY = true;
			break;
		case CV_EVENT_RBUTTONDOWN:
			roadTexture = "mudcon"; // mud or concrete Road
			TRAIN = true;
			break;
		case CV_EVENT_RBUTTONUP:
			CLASSIFY = false;
			break;
		case CV_EVENT_MBUTTONDOWN:
			break;
		case CV_EVENT_MBUTTONUP:
			break;
		default:
			break;
	}
}
void mudcon( int event, int x, int y, int flags, void* param )
{	
	switch( event ){
		case CV_EVENT_MOUSEMOVE: 
			break;
		case CV_EVENT_LBUTTONDOWN:
			//start recording
			TRAIN = true;
			roadTexture = "mud";// mud Road
			break;
		case CV_EVENT_LBUTTONUP:
			CLASSIFY = true;
			break;
		case CV_EVENT_RBUTTONDOWN:
			roadTexture = "con"; // concrete Road
			TRAIN = true;
			break;
		case CV_EVENT_RBUTTONUP:
			CLASSIFY = false;
			break;
		case CV_EVENT_MBUTTONDOWN:
			break;
		case CV_EVENT_MBUTTONUP:
			break;
		default:
			break;
	}
}

void onMouse2( int event, int x, int y, int flags, void* param )
{	
	switch( event ){
		case CV_EVENT_MOUSEMOVE: 
			break;
		case CV_EVENT_LBUTTONDOWN:
			//start recording
			TRAIN = true;
			roadCondition=0;
			break;
		case CV_EVENT_LBUTTONUP:
			//stop recording
			//TRAIN = false;
			CLASSIFY = true;
			break;
		case CV_EVENT_RBUTTONDOWN:
			TRAIN = true;
			roadCondition=1;
			break;
		case CV_EVENT_RBUTTONUP:
			//TRAIN = false;
			CLASSIFY = false;
			break;
		case CV_EVENT_MBUTTONDOWN:
			TRAIN = true;
			roadCondition=2;
			break;
		case CV_EVENT_MBUTTONUP:
			//TRAIN = false;
			break;
		default:
			break;
	}
}

void onMouse3( int event, int x, int y, int flags, void* param )
{	
	switch( event ){
		case CV_EVENT_MOUSEMOVE: 
			break;
		case CV_EVENT_LBUTTONDOWN:
			//start recording
			TRAIN = true;
			roadCondition=3;
			break;
		case CV_EVENT_LBUTTONUP:
			//stop recording
			//TRAIN = false;
			CLASSIFY = true;
			break;
		default:
			break;
	}
}


int main() 
{ 
	switchOFF = false;
	//Class Objects/////////////////////////////////////////////////////
	GPSProcessing *gpsDataPrs;
	ACCProcessing *accDataPrs;
	CAMProcessing *camDataPrs;
	Serial		  *comObj;
	//Local Variables////////////////////////////////////////////////////
	char resultsData[150];
	int option;
	void *param=0;
	bool readMapFlag=true;
	int key=0;
	ifstream dataFile;
	string line="";
	vector <loc> wayPt;vector <vector<loc>> wayGrp;
	vector <mapNode> mapNodes; vector <vector <mapNode>> mapNetwork;
		

    //Class Instances---------------------------------------------------------
	gpsDataPrs = new GPSProcessing();
	accDataPrs = new ACCProcessing();
	camDataPrs = new CAMProcessing();
	comObj     = new Serial("COM1");

	//oriDataPrs = new ORIThread();

	//--------------------------------------------------------------------
	cv::Mat gpsMap(800,800,CV_32FC3,cv::Scalar(0));
	Mat accPlot (PLOT_HT,BUF_SIZE,CV_32FC3,Scalar(0));
	cv::Mat quit(100,100,CV_32FC3,cv::Scalar(0));
	cv::Mat RT(100,100,CV_32FC3,cv::Scalar(0));
	cv::Mat RC(100,100,CV_32FC3,cv::Scalar(0));

	cv::namedWindow("quit",1);
	imshow("quit",quit);
	cv::namedWindow("tarmudcon_RT",1);
	imshow("tarmudcon_RT",RT);
	cv::namedWindow("mudcon_RT",1);
	imshow("mudcon_RT",RT);

	cv::namedWindow("RC",1);
	cv::namedWindow("poor_RC",1);
	imshow("RC",RC);
	imshow("poor_RC",RC);
	cv::namedWindow("camPIC",1);

	//main loop for training and classification---------------------------
	while((key = cv::waitKey(0)) != 0x1b)
	{	
		cout<<"Project Highway"<<endl;
		cout<<"Options"<<endl<<"1. Training"<<endl<<"2. Classification"<<endl<<"3.Break Out"<<endl;
		cin>>option;

		//Common steps for both training and classification
		cv::setMouseCallback("camPIC", chooseBox, (void*)&param);
		cv::setMouseCallback("tarmudcon_RT", tarmudcon, (void*)&param);
		cv::setMouseCallback("mudcon_RT", mudcon, (void*)&param);
		cv::setMouseCallback("RC", onMouse2, (void*)&param);
		cv::setMouseCallback("poor_RC", onMouse3, (void*)&param);
		dataFile.open("Data\\Data.txt",ios::in);

		//perform training
		if(option==1)
		{
			//sub loop to select what kind of training
			cout<<"What kind of training?"<<endl;
			cout<<"Options"<<endl<<"1. Road Texture"<<endl<<"2. Road Condition"<<endl<<"3.Break Out"<<endl;
			cin>>option;
			cout<<"Left click for Tar, Right click for mud, Middle click for concrete in the RT window"<<endl;

			if (option==1)
			//read the sample count
				camDataPrs->readSampleCount();
			while((key = cv::waitKey(1)) != 0x1b)
			{
				//function to update the central sensor structure
				get_sensor_data(&line,&dataFile,comObj);

				//function to display gps map and accelerometer plot and display the snaps
				//dis_sensor_data(gpsDataPrs,accDataPrs,camDataPrs,&readMapFlag,&gpsMap,&wayPt,&wayGrp,&accPlot);
				dis_sensor_data(gpsDataPrs,accDataPrs,camDataPrs,&readMapFlag,&gpsMap,&wayPt,&wayGrp,&accPlot,&mapNodes,&mapNetwork);

				if(NewFile)
				{
					NewFile = false;
					waitKey(0);
				}
				if(option==1){
					if (TRAIN && boxPresent)
						camDataPrs->train();
				}
				else if (option==2)
				{
					if (TRAIN)
					accDataPrs->train();
				}
				else
					break;
			}
			if (option==1)
			//finish the Camera training by updating the database file
				camDataPrs->updateSampleCount();
		}
		else if (option==2)
		{
			//read the sample counts in the database before starting the classification
			camDataPrs->readSampleCount();
			char ch;
			//prepare the Maperitive file for displayin the results
			ifstream myfile1 ("texture2.osm");
			ofstream mapfile1 ("texture1.osm");
			while(myfile1.get(ch)) 
			mapfile1.put(ch);
			myfile1.close();
			mapfile1.close();
//-----------------------------------------------------------------------
			//reading the training file
			ifstream trfile;
			string line;
			float tempVec[FEATURE_VC_LN];
			for (unsigned int i=0;i<FEATURE_VC_LN;i++)
				tempVec[i]=0;
			trfile.open("my_accleration.txt",ios::in);
			if(trfile.is_open())
			{
				while(getline(trfile,line))
				{
					const char* c_line =line.c_str();
					cout<<line<<endl;
					
					sscanf_s(c_line,"%f %f %f %f %f",&tempVec[0],&tempVec[1],&tempVec[2],&tempVec[3],&tempVec[4]);
					for(unsigned int i=0;i<FEATURE_VC_LN;i++)
						trainingDataElement.push_back(tempVec[i]);
					trainingDataSet.push_back(trainingDataElement);
					trainingDataElement.clear();
				}
				trfile.close();
			}
//			cout<<"size"<<trainingDataSet.size();
//---------------------------------------------------------------

			//classification loop
			ofstream resultsFile;
			resultsFile.open("result.txt");
			while((key = cv::waitKey(1)) != 0x1b)
			{
				//function to update the central sensor structure
				get_sensor_data(&line,&dataFile,comObj);
				//function to display gps map and accelerometer plot and display the snaps
				dis_sensor_data(gpsDataPrs,accDataPrs,camDataPrs,&readMapFlag,&gpsMap,&wayPt,&wayGrp,&accPlot,&mapNodes,&mapNetwork);

				//NewFile is the bool that says that new camera image is available. Indirectly we are setting a 
				//classification frequency of 2 seconds
				if(NewGPS)
				{
					if(CLASSIFY && liveData.speed>5)
						accDataPrs->classify(liveData.lat,liveData.lon);
				}

					//if (CLASSIFY && boxPresent && NewFile)
					//{			
					//	
					//	camDataPrs->camPothole();
					//	camDataPrs->classify(liveData.lat,liveData.lon);
					//}

				if((CLASSIFY) && (NewGPS) && (liveData.speed>5))
					{
				//		//updateGIS();
						NewGPS = false;
						cout<<roadConditionResult<<endl;
						sprintf_s(resultsData,"%f,%f,%s,%f\n",corGPSPt.lat,corGPSPt.lon,roadConditionResult.c_str(),RMSDX);						
						cout <<"RMSDX: "<<RMSDX<<endl;
						resultsFile<<resultsData;
					}

				///	if (CLASSIFY && boxPresent && NewFile)
				//	{			
				//		NewFile = false;
				//		cout<<roadSurfaceResult<<endl;
				//		sprintf_s(resultsData,"%f,%f,%s\n",corGPSPt.lat,corGPSPt.lon,roadSurfaceResult.c_str());						
				  //    resultsFile<<resultsData;
					//}
			}
			resultsFile.close();	
			}
			
	}
	switchOFF = true;

	return 0;
}

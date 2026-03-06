#include "ACCProcessing.h"
#include "global.h"
#include <deque>

//Global Variables
static bool switchOFF;
extern sensorData liveData;
extern sensorData prevData;
extern bool TRAIN;
extern int roadCondition;
extern loc corGPSPt;
//------------------
extern string roadConditionResult;
//------------------

using namespace std;

#define K_NN 5

std::deque<double> timeStamp;
std::deque<loc>gpsTrack;
std::deque<double> ACC_ValuesX;
std::deque<double> ACC_ValuesY;
std::deque<double> ACC_ValuesZ;

std::deque<double> ACC_ValuesX_s;
std::deque<double> ACC_ValuesY_s;
std::deque<double> ACC_ValuesZ_s;
std::deque<double> DIST_Values;
extern double RMSDX;
extern double RMSDY;
extern double RMSDZ;
int thres_ptCntX;
int thres_ptCntY;
int thres_ptCntZ;
extern vector <vector <float>> trainingDataSet;
extern vector <float> trainingDataElement;
vector <float> liveDataElement;
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

ACCProcessing::ACCProcessing()
{
}

ACCProcessing::~ACCProcessing()
{
}

void plotAcc(Mat accPlot)
{
	if(ACC_ValuesY.empty())
		return;
	accPlot.setTo(Scalar(0));
	for(int i=0;i<ACC_ValuesY.size()-1;i++)
	{
		//cv::line(accPlot,cv::Point2f(i,(ACC_ValuesY.at(i)*10 + (accPlot.rows)/2)),cv::Point2f(i,ACC_ValuesY.at(i+1)*10 + (accPlot.rows)/2),Scalar(255,255,255),1,8,0);
		cv::line(accPlot,cv::Point2f(5*i,(ACC_ValuesY.at(i)*10 + 0               )),cv::Point2f(5*(i+1),(ACC_ValuesY.at(i+1)*10 + 0            )),Scalar(255,255,0),1,8,0);
		cv::line(accPlot,cv::Point2f(5*i,(ACC_ValuesZ.at(i)*10 +(accPlot.rows)/2)),cv::Point2f(5*(i+1),(ACC_ValuesZ.at(i+1)*10 + (accPlot.rows)/2)),Scalar(255,0,255),1,8,0);
		cv::line(accPlot,cv::Point2f(5*i,(ACC_ValuesX.at(i)*10 +(accPlot.rows)/2)),cv::Point2f(5*(i+1),(ACC_ValuesX.at(i+1)*10 + (accPlot.rows)/2)),Scalar(0,255,255),1,8,0);
	}
	cv::imshow("Acc_Plot",accPlot);
}

double gpsDistance(loc presPOS, loc prevPOS) 
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


void ACCProcessing::processACC(Mat *accPlot)
{

	static double sumSqrX=0;
	static double sumSqrY=0;
	static double sumSqrZ=0;

	static double sumX=0;
	static double sumY=0;
	static double sumZ=0;

	double intraPtDist=0;
	static loc presPOS,prevPOS;
	static double distTvld=0;
	static double timeDiff=0;
	
	//-----------------------------------------------------------------
	plotAcc(*accPlot);

	//timeDiff calculation-----------------------------------------
	timeStamp.push_back(liveData.timestamp);//0
	timeDiff = liveData.timestamp - timeStamp.front();

	if((liveData.lat == 17.44799623) && (liveData.lon == 78.35853488 ))
		cout << "break here "<<endl;
	//distance calculation-----------------------------------------
	prevPOS.lat = presPOS.lat;prevPOS.lon = presPOS.lon;
	presPOS.lat = corGPSPt.lat;presPOS.lon = corGPSPt.lon;
	intraPtDist = gpsDistance(presPOS, prevPOS);
	if(intraPtDist>10000)
		return;
	distTvld = distTvld + intraPtDist;
			
	//SD of XYZ
	//Finding RMSDY---element 1 of feature vector-------
	ACC_ValuesY.push_back(liveData.accY);
	sumY = sumY + ACC_ValuesY.back();
	double meanY= sumY/ACC_ValuesY.size();
	ACC_ValuesY_s.push_back((liveData.accY-meanY)* (liveData.accY-meanY));
	sumSqrY = sumSqrY + ACC_ValuesY_s.back();
	RMSDY = sqrt(sumSqrY / ACC_ValuesY_s.size());
	//cout <<"RMSDY: "<<RMSDY<<endl;
	//Finding RMSDX---element 2 of feature vector-------
	ACC_ValuesX.push_back(liveData.accX);
	sumX = sumX + ACC_ValuesX.back();
	double meanX= sumX/ACC_ValuesX.size();
	ACC_ValuesX_s.push_back((liveData.accX-meanX)* (liveData.accX-meanX));
	sumSqrX = sumSqrX + ACC_ValuesX_s.back();
	RMSDX = sqrt(sumSqrX / ACC_ValuesX_s.size());
//	cout <<"RMSDX: "<<RMSDX<<endl;
	//Finding RMSDZ---element 3 of feature vector-------
	ACC_ValuesZ.push_back(liveData.accZ);
	sumZ = sumZ + ACC_ValuesZ.back();
	double meanZ= sumZ/ACC_ValuesZ.size();
	ACC_ValuesZ_s.push_back((liveData.accZ-meanZ)* (liveData.accZ-meanZ));
	sumSqrZ = sumSqrZ + ACC_ValuesZ_s.back();
	RMSDZ = sqrt(sumSqrZ / ACC_ValuesZ_s.size());
	//cout <<"RMSDZ: "<<RMSDZ<<endl;
	//-----------------------------------------------------------------------
	//element 4 is GPS speed
	//-----------------------------------------------------------------------
	//cout <<"Speed: "<<liveData.speed<<endl;	
	//cout <<endl;	
	//to calculate over all distance
	DIST_Values.push_back(intraPtDist);//3
	gpsTrack.push_back(presPOS);//4

	//2SEC_WINDOW--------------------------------------------------
	if(timeDiff>TWO_SEC_WINDOW)
	{
		while (timeDiff>TWO_SEC_WINDOW)
		{
			
			if(ACC_ValuesY.size()==0)
				break;
			//house keep the Y data
			sumSqrY  = sumSqrY - ACC_ValuesY_s.front();		
			sumY     = sumY - ACC_ValuesY.front();		
			ACC_ValuesY.pop_front();
			ACC_ValuesY_s.pop_front();
			//house keep the X data
			sumSqrX  = sumSqrX - ACC_ValuesX_s.front();		
			sumX     = sumX - ACC_ValuesX.front();		
			ACC_ValuesX.pop_front();
			ACC_ValuesX_s.pop_front();
			//house keep the Z data
			sumSqrZ  = sumSqrZ - ACC_ValuesZ_s.front();		
			sumZ     = sumZ - ACC_ValuesZ.front();		
			ACC_ValuesZ.pop_front();
			ACC_ValuesZ_s.pop_front();

			timeDiff = liveData.timestamp - timeStamp.front();
			timeStamp.pop_front();
		}
	}
	//------------------------------------------------------------

	//if (distTvld > X) reduce the buffer content------------------
	if (distTvld > DIST_THRESH_M)
	{
		/*--------------------------------------------------------
		//gps debug
		double gpsDist=0;
		for(unsigned int i=0;i<gpsTrack.size()-1;i++)
		{
			if((gpsTrack.at(i).lat!=gpsTrack.at(i+1).lat)&&(gpsTrack.at(i).lon!=gpsTrack.at(i+1).lon)
				&&(gpsTrack.at(i).lat!=0)&&(gpsTrack.at(i).lon!=0)
				&&(gpsTrack.at(i+1).lat!=0)&&(gpsTrack.at(i+1).lon!=0))
			{
				gpsDist= gpsDist+gpsDistance(gpsTrack.at(i), gpsTrack.at(i+1));
			}
		}
		cout <<"gps dist"<<gpsDist<<endl;
		//--------------------------------------------------------*/
		while (distTvld > DIST_THRESH_M)
		{
			distTvld = distTvld - DIST_Values.front();
			gpsTrack.pop_front();
			DIST_Values.pop_front();
		}
	}
	//in case the buffer overflows
	if(gpsTrack.size()>BUF_SIZE)
	{
		distTvld = distTvld - DIST_Values.front();
		gpsTrack.pop_front();
		DIST_Values.pop_front();
	}
}

void ACCProcessing::train()
{
	TRAIN=false;
	char buff[100];
	float tempVec[5];
	FILE *fp;
	fp=fopen("my_accleration.txt","a");
	//if (!fp.isOpened()) {std::cout << "unable to open file storage!" << std::endl; return;}
	sprintf_s(buff,"%f %f %f %f %d",RMSDY,RMSDX,RMSDZ,liveData.speed,roadCondition);
	tempVec[0]=RMSDY;
	tempVec[1]=RMSDX;
	tempVec[2]=RMSDZ;
	tempVec[3]=liveData.speed;
	tempVec[4]=roadCondition;
	for(unsigned int i=0;i<FEATURE_VC_LN;i++){
		trainingDataElement.push_back(tempVec[i]);}

		trainingDataSet.push_back(trainingDataElement);
		trainingDataElement.clear();


	fprintf(fp,"%s \n",buff);
	fclose(fp);
}

bool compareVectors(vector <float> a,vector <float> b)
{
	return (a.at(0)<b.at(0));
}

void plotGeoPts_(vector <loc> geoPts, int roadType)
{

	ifstream myfile ("texture1.osm");
	ofstream mapfile ("texture.osm");
	std::string line;
	std::string line1;
	static long node_id = 1128727666;
	double lat;
	double lon;
	while (std::getline(myfile, line))
	{
		
		if(line== "</osm>")
		{
			if(roadType==0)
			{
				for(int i=0;i<geoPts.size();i++)
				{
					lat = geoPts.at(i).lat;
					lon = geoPts.at(i).lon;
					//line1 = "<node id='1128727666' lat='%f' lon='%f'>";
					mapfile<<"<node id='"<<node_id ++<< "' lat='" <<format("%0.6f",lat) << "' lon='" << format("%0.6f",lon) <<"'>"<<endl;
					line1 = "<tag k='amenity' v='place_of_worship'/>";
					mapfile<<line1<< endl;
	    			line1 = "<tag k='religion' v='christian'/>";
					mapfile<<line1<< endl;
					line1 = "</node>";
					mapfile<<line1<< endl;
				}
			}
			else if(roadType==1)
			{
				for(int i=0;i<geoPts.size();i++)
				{
					lat = geoPts.at(i).lat;
					lon = geoPts.at(i).lon;
					//line1 = "<node id='1128727666' lat='%f' lon='%f'>";
					mapfile<<"<node id='"<<node_id ++<< "' lat='" <<format("%0.6f",lat) << "' lon='" << format("%0.6f",lon) <<"'>"<<endl;
					line1 = "  <tag k='amenity' v='bank'/>";
					mapfile<<line1<< endl;
					line1 = "</node>";
					mapfile<<line1<< endl;
				}
			}
			else if (roadType==2)
				for(int i=0;i<geoPts.size();i++)
				{
					lat = geoPts.at(i).lat;
					lon = geoPts.at(i).lon;
					//line1 = "<node id='1128727666' lat='%f' lon='%f'>";
					mapfile<<"<node id='"<<node_id ++<< "' lat='" <<format("%0.6f",lat) << "' lon='" << format("%0.6f",lon) <<"'>"<<endl;
					line1 = "  <tag k='amenity' v='fast_food'/>";
					mapfile<<line1<< endl;
					line1 = "</node>";
					mapfile<<line1<< endl;
				}

		}
		mapfile<<line<< endl;
	}
	myfile.close();
	mapfile.close();
	
	char ch;
	ifstream myfile1 ("texture.osm");
	ofstream mapfile1 ("texture1.osm");
    while(myfile1.get(ch)) 
       mapfile1.put(ch);
	myfile1.close();
	mapfile1.close();
}

void ACCProcessing::classify(double lat, double lon)
{	
	//cout<<"in classifier";
	float eucliDist=0;
	vector <float> dist_and_class;
	vector <vector <float>> all_dist_and_class;
	all_dist_and_class.clear();
	liveDataElement.clear();
	liveDataElement.push_back(RMSDY);
	liveDataElement.push_back(RMSDX);
	liveDataElement.push_back(RMSDZ);
	liveDataElement.push_back(liveData.speed);
	//liveDataElement.push_back(0);
//	cout<<trainingDataSet.size();
	for(unsigned int i=0;i<trainingDataSet.size();i++)
	{
		trainingDataElement = trainingDataSet.at(i);
		eucliDist = CalculateEuclidean(trainingDataElement,liveDataElement);
		dist_and_class.push_back(eucliDist);//push distance
		dist_and_class.push_back(trainingDataElement.at(4));//push class
		all_dist_and_class.push_back(dist_and_class);
		dist_and_class.clear();
	}
	//sort the all_dist_and_class vector based on the distance(first vector element)
	std::sort(all_dist_and_class.begin(),all_dist_and_class.end(),compareVectors);
	int road_class[4];
	for(unsigned int i=0;i<4;i++)//4 is class  count
		road_class[i]=0;
	for (unsigned int i=0;i<K_NN;i++)
	{
		//cout<<(int)all_dist_and_class.at(i).at(1)<<endl;
		switch((int)all_dist_and_class.at(i).at(1))
		{
		case 0:
			road_class[0]++;
			break;
		case 1:
			road_class[1]++;
			break;
		case 2:
			road_class[2]++;
			break;
		case 3:
			road_class[3]++;
			break;
		default:
			cout<<"something wrong"<<endl;
		}
	}

	int largest=0;
	int idx=0;
	for(unsigned int i=0;i<4;i++)
		if(road_class[i]>largest)
		{
			largest = road_class[i];
			idx = i;
		}
	roadCondition = idx;
	if(roadCondition==0)
		roadConditionResult="good";
	if(roadCondition==1)
		roadConditionResult="satisfactory";
	if(roadCondition==2)
		roadConditionResult="unsatisfactory";
	if(roadCondition==3)
		roadConditionResult="poor";

	loc geoPt;
	vector <loc> geoPts;
	geoPt.lat = lat;
	geoPt.lon = lon;
	geoPts.push_back(geoPt);
	plotGeoPts_(geoPts,roadCondition);
}

float ACCProcessing::CalculateEuclidean(vector<float> vec1,vector<float> vec2)
{
	float distance = 0;

	for (unsigned int i=0;i<vec2.size();i++)//vec1 will have one extra element(class)
	{
		distance = distance  + pow(vec1.at(i)-vec2.at(i),2);
	}
	return sqrt(distance);
}




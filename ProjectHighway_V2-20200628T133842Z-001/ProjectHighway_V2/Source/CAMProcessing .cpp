#include "global.h"
#include "CAMProcessing.h"
#include <string>
#include <iostream>
#include <fstream>
#include <windows.h>
#include <boost/date_time/posix_time/posix_time.hpp>
#define CLASS_CNT 4
#define K_NN 5

//Global Variables
static bool switchOFF;
double c_timestamp;
int BOX_Ox=0;
int BOX_Oy=0;
int BOX_H =60;
int BOX_W =120;
int Classify_Flag;
unsigned int Sample_Cnt[CLASS_CNT];
cv::Mat Box(2,2,CV_32F,cv::Scalar(0));
extern bool TRAIN;
extern std::string roadTexture;
extern cv::Mat camPIC_copy;

using namespace std;
using namespace cv;
extern string roadSurfaceResult;
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////
double CAMtimestamp;

CAMProcessing::CAMProcessing()
{
}

CAMProcessing::~CAMProcessing()
{
}

void CAMProcessing::camPothole(void)
{
	Mat edge,cedge;
	int threshval = 30;
    vector<vector<Point> > contours;
    vector<Vec4i> hierarchy;
	Mat subImg(camPIC_copy, Rect(BOX_Ox,BOX_Oy,BOX_W,BOX_H));
	cv::cvtColor(subImg,edge,CV_BGR2GRAY);
	imshow("Edge map", edge);
	waitKey(1);
    // Run the edge detector on grayscale
    Canny(edge, edge, threshval, threshval*3, 3);
    cedge = Scalar::all(0); 
    edge.copyTo(cedge);

    findContours( cedge, contours, hierarchy, CV_RETR_CCOMP, CV_CHAIN_APPROX_SIMPLE );
	
	Mat dst = Mat::zeros(subImg.size(), CV_8UC3);

    if( !contours.empty() && !hierarchy.empty() )
    {
        // iterate through all the top-level contours,
        // draw each connected component with its own random color
        int idx = 0;
        for( ; idx >= 0; idx = hierarchy[idx][0] )
        {
            Scalar color( (rand()&255), (rand()&255), (rand()&255) );
            drawContours( dst, contours, idx, color, CV_FILLED, 8, hierarchy );

			///cout<<cv::contourArea(contours.at(idx))<<endl;

        }
    }

	dst.copyTo(cedge);
    imshow("Edge map", dst);

}
/*	
void CAMProcessing::startCAM(void* param)
{
	const char* c_line;
	double tmp1 = 0;
	double m_time1 = 0;
	double m_time2 = 0;
	string line1 = "";
	string filename= "";
	int picNumber  = 1;
	double delay =0;
	

	ifstream camPICFile("Data//CAMPIC2014-10-30-09-42-24.csv");
	Mat camPIC;
	
	//read the initial sensor timestamp--------------------
	if(!getline(camPICFile, line1))
		_endthread();
	else
	{
		c_line =line1.c_str();
		sscanf_s(c_line,"%lf,%lf",&tmp1,&m_time1);
	}

	time_t t = std::time(0);
	c_timestamp = 0.404490310;
	double milliseconds;
	boost::posix_time::ptime now = boost::posix_time::microsec_clock::local_time();
	boost::posix_time::time_duration td = now.time_of_day();
	milliseconds=(td.total_milliseconds())/86400000.0;
	double timestamp_offset = milliseconds - c_timestamp;

	while(getline(camPICFile, line1))
	{
		//delay is calculated as per the timestamp
		c_line =line1.c_str();
		sscanf_s(c_line,"%lf,%lf",&tmp1,&m_time2);
		//sync

		while(c_timestamp<m_time2)
		{
			now = boost::posix_time::microsec_clock::local_time();
			td = now.time_of_day();
			c_timestamp = ((td.total_milliseconds())/86400000.0)-timestamp_offset;
		}

		cout <<"CAM "<< c_timestamp <<" "<<m_time2<<endl; // time sync
		delay = (m_time2-m_time1)*86400000;
		//cout<<delay<<endl;
		//readimage
		stringstream convert;
		convert << picNumber;
		filename = "Data//IMG_" + convert.str()+".jpg";
		picNumber +=2;
		camPIC = cv::imread(filename,1);

		//imshow
		namedWindow("camPIC");
		imshow("camPIC",camPIC);
		//Sleep(delay);
		cv::waitKey(1); //wait in milli seconds
		m_time1 = m_time2;
		if(switchOFF)
			break;
	}
	_endthread();
}


void CAMProcessing::beginCAMProcessing()
{
	void *param=0;
	_beginthread(startCAM,0,param);
}

void CAMProcessing::stopCAMProcessing()
{
	switchOFF = true;
}
*/

Mat CAMProcessing::Get_subImage(Mat image, int HSI_X)
{
	namedWindow("subimage",1);
	Mat subImage(image, Rect(BOX_Ox,BOX_Oy,BOX_W,BOX_H));
	Mat subImageHSV;
	Mat subImageH_S_V[3];
	cv::cvtColor(subImage,subImageHSV,COLOR_BGR2HSV);
	split(subImageHSV,subImageH_S_V);
	
	imshow("subimage",subImageH_S_V[HSI_X]);
	return subImageH_S_V[HSI_X];
}

void CAMProcessing::updateSampleCount(void)
{
		Mat countMatrix (1,4,CV_32F,Scalar(0));
		for(int i=0;i<CLASS_CNT;i++)
			countMatrix.at<float>(0,i) = (float)Sample_Cnt[i];
		cv::FileStorage fs("SampleCount.yml", cv::FileStorage::WRITE);
		fs <<"countMatrix"<<countMatrix;
		fs.release();
}

void CAMProcessing::readSampleCount(void)
{
	cv::FileStorage fs("sampleCount.yml", cv::FileStorage::READ);
	if(fs.isOpened())
	{
		Mat countMatrix (1,4,CV_32F,Scalar(0));
		fs["countMatrix"] >> countMatrix;
		for(int i=0;i<CLASS_CNT;i++)
			Sample_Cnt[i]= countMatrix.at<float>(0,i);
		fs.release();
	}
	else
	{
		Mat countMatrix (1,4,CV_32F,Scalar(0));
		cv::FileStorage fs("SampleCount.yml", cv::FileStorage::WRITE);
		fs <<"countMatrix"<<countMatrix;
		fs.release();
	}
}

void drawHist(Mat hist)
{
	cv::Mat histDig(50,90,CV_32FC3,cv::Scalar(0));
	namedWindow("histogram");
	cv::Point2f plotPt;
	cv::Point2f tempPt;
	tempPt.x =0;
	tempPt.y =50;
	for(int i=0;i<30;i++)
	{
		plotPt.y = (50 - (hist.at<float>(i,0)/9333.0)*50); //histogram total - normalize
		plotPt.x = i*3;
		cv::line(histDig,plotPt,tempPt,Scalar(255,0,255),1,8,0);
		tempPt = plotPt;
	}
	imshow("histogram",histDig);
	
}

bool compareVectors_H(vector <float> a,vector <float> b)
{
	return (a.at(0)<b.at(0));
}

unsigned int compareHistogram(Mat hist, cv::FileStorage fs,vector<std::string> *className,int start)
{
	Mat trainHist;
	char histName[100];
	int roadType;

	vector <float> value_and_class;
	vector <vector <float>> all_value_and_class;

	for(unsigned int i=0;i<className->size();i++)
	{
		for(unsigned int j=1;j<=Sample_Cnt[start+i];j++)
		{
			sprintf_s(histName,"histogram_class_%s_%d\0",className->at(i).c_str(),j);
			fs [histName] >> trainHist;
			double cmpValue = cv::compareHist(trainHist,hist,CV_COMP_BHATTACHARYYA);
			value_and_class.push_back(cmpValue);
			value_and_class.push_back(i);//class
			all_value_and_class.push_back(value_and_class);
			value_and_class.clear();
		}
	}
	//sort the all_dist_and_class vector based on the distance(first vector element)
	std::sort(all_value_and_class.begin(),all_value_and_class.end(),compareVectors_H);

	//count the class types 
	int road_class[CLASS_CNT];
	for(unsigned int i=0;i<CLASS_CNT;i++)
		road_class[i]=0;
	for (unsigned int i=0;i<K_NN;i++)
	{
		switch((int)all_value_and_class.at(i).at(1))
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
	for(unsigned int i=0;i<CLASS_CNT;i++)
		if(road_class[i]>largest)
		{
			largest = road_class[i];
			idx = i;
		}
	roadType = idx;
//	cout<<"Road Texture "<<roadType<<endl;
	return roadType;
}
unsigned int whatClass(string roadTexture)
{
	if(strcmp(roadTexture.c_str(),"tar")==0)
		return 0;
	if(strcmp(roadTexture.c_str(),"mudcon")==0)
		return 1;
	if(strcmp(roadTexture.c_str(),"mud")==0)
		return 2;
	if(strcmp(roadTexture.c_str(),"con")==0)
		return 3;
	return 4;
}
void CAMProcessing::train()
{
	Mat sub_image;
	TRAIN = false;
	Mat hist;
	char histName[100];
	char fileName[100];
	int hbins = 30;//hue to 30 levels
	int histSize[]={hbins};
	float hranges[] = {0,180};
	int channels[] = {0};
	const float* ranges[] = {hranges};
	
	//DEBUG CODE
	Mat subImg(camPIC_copy, Rect(BOX_Ox,BOX_Oy,BOX_W,BOX_H));
	sprintf_s(fileName,"camLearn\\image_class_%s_%d.jpg\0",roadTexture.c_str(),++Sample_Cnt[whatClass(roadTexture)]);//increment the sample count of the class
	cv::imwrite(fileName,subImg);
	//END OF DEBUG CODE

	if((whatClass(roadTexture)==0)||(whatClass(roadTexture)==1))//mud or tar
		sub_image = Get_subImage(camPIC_copy,HSI_I);
	if((whatClass(roadTexture)==2)||(whatClass(roadTexture)==3))//mud or con
		sub_image = Get_subImage(camPIC_copy,HSI_S);
	cv::calcHist(&sub_image,1,channels,Mat(),hist, 1,histSize,ranges);
	cv::FileStorage fs("my_histogram_file.yml", cv::FileStorage::APPEND);
	if (!fs.isOpened()) {std::cout << "unable to open file storage!" << std::endl; return;}
	sprintf_s(histName,"histogram_class_%s_%d\0",roadTexture.c_str(),Sample_Cnt[whatClass(roadTexture)]);//increment the sample count of the class
	
	fs << histName<< hist;
	fs.release();
	drawHist(hist);
}

void plotGeoPts(vector <loc> geoPts, int roadType)
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
			if(roadType==0)//unpaved - mud
			{
				for(unsigned int i=0;i<geoPts.size();i++)
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
			else if(roadType==1)//tar
			{
				for(unsigned int i=0;i<geoPts.size();i++)
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
			else if (roadType==2)//con
				for(unsigned int i=0;i<geoPts.size();i++)
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


void CAMProcessing::classify(double lat, double lon)
{
	cv::FileStorage fs("my_histogram_file1.yml", cv::FileStorage::READ);
	if (!fs.isOpened()) {std::cout << "unable to open file storage!" << std::endl; return;}
	vector<string>className;

	Mat hist;
	int hbins = 30;//hue to 30 levels
	int histSize[]={hbins};
	float hranges[] = {0,180};
	int channels[] = {0};
	const float* ranges[] = {hranges};
	int key =0;
	loc geoPt;
	vector <loc> geoPts;
	geoPts.clear();
	//Sleep(2000);
	Mat subImage = Get_subImage(camPIC_copy,HSI_I);
	cv::calcHist(&subImage,1,channels,Mat(),hist, 1,histSize,ranges);
	//what are the classes should compareHistogram classify
	className.clear();
	className.push_back("tar");
	className.push_back("mudcon");
	unsigned int outPutclass = compareHistogram(hist,fs,&className,0);

	if (outPutclass==0)
		roadSurfaceResult = "tar";
	else if (outPutclass==1)
	{
	//	cout<<"paved road"<<endl;
		
		subImage = Get_subImage(camPIC_copy,HSI_S);
		cv::calcHist(&subImage,1,channels,Mat(),hist, 1,histSize,ranges);
		//what are the classes should compareHistogram classify
		className.clear();
		className.push_back("mud");
		className.push_back("con");
		outPutclass = compareHistogram(hist,fs,&className,2);
		if(outPutclass ==0)
			roadSurfaceResult = "mud";

		else if (outPutclass==1)
			roadSurfaceResult = "con";

			outPutclass = outPutclass+2;// this is for plotgeopts
		
	}

	fs.release();
	//draw on map - this may not be required to be done using maperative
	geoPt.lat = lat;
	geoPt.lon = lon;
	geoPts.push_back(geoPt);
	
	plotGeoPts(geoPts,outPutclass);
	
}

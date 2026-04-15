#include <process.h>
#include <opencv2/core.hpp>
#include <opencv2/imgproc.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/calib3d.hpp>

#define HSI_H 0
#define HSI_S 1
#define HSI_I 2

class CAMProcessing
{
private:
	
	
public:
	CAMProcessing();
	virtual ~CAMProcessing();	
	void camPothole(void);
	cv::Mat Get_subImage(cv::Mat image,int HSI_X);
	void updateSampleCount(void);
	void readSampleCount(void);
	void train(void);
	void classify(double lat, double lon);
};
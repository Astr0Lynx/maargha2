#include <process.h>
#include <stdio.h>
#include <Windows.h>


class TIMThread
{
public:
	TIMThread();
	virtual ~TIMThread();	
	static void TIMThread::startTIME(void* param);
	void beginTIMThread(void);
	void stopTIMThread(void);
};
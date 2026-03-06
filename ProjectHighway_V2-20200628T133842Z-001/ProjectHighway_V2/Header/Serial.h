#include<windows.h> 
#include<iostream>

using namespace std;

 
class Serial
{
private:
	HANDLE hPort;
	DCB dcb;
public:
	Serial(char* COMX);
	~Serial();
	bool writebyte(char* data);
	int ReadByte(void);
	void writeData(char* data);
};
#include "Serial.h"

 


Serial::Serial(char* COMX)
{
	// Initialize the serial port variable and parameters 
	hPort = CreateFile(COMX, 
	GENERIC_WRITE|GENERIC_READ,0,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,NULL);
}

Serial::~Serial()
{
	CloseHandle(hPort);
}

/*********************Function for Sending Data***********************/ 
bool Serial::writebyte(char* data) 
{ 
	DWORD byteswritten; 
	if (!GetCommState(hPort,&dcb)) 
	{ 
		cout<<"\nSerial port cant b opened\n"; 
		return false; 
	} 
	dcb.BaudRate = CBR_115200;  //115200 Baud 
	dcb.ByteSize = 8;                  //8 data bits 
	dcb.Parity = NOPARITY;    //no parity 
	dcb.StopBits = ONESTOPBIT; //1 stop 
	 
	if (!SetCommState(hPort,&dcb)) //If Com port cannot be configured accordingly 
	return false; 
	 
	bool retVal = WriteFile(hPort,data,1,&byteswritten,NULL); //Write the data to be sent to Serial port  
return retVal; // return true if the data is written 
} 
 
int Serial::ReadByte() 
{ 
	int Val; 
	BYTE Byte; 
	DWORD dwBytesTransferred; 
	DWORD dwCommModemStatus; 
	if (!GetCommState(hPort,&dcb)) 
	return 0; 
	SetCommMask (hPort, EV_RXCHAR | EV_ERR); //receive character event 
	WaitCommEvent (hPort, &dwCommModemStatus, 0); //wait for character 
	if (dwCommModemStatus & EV_RXCHAR) 
	ReadFile (hPort, &Byte, 1, &dwBytesTransferred, 0); 
	Val = Byte; 
return Val; 
} 
 
void Serial::writeData(char* data)
 {
	int idx =0;
	while(1)
	{
		if(data[idx] =='\0')
			break;
		else
		{
		if(writebyte(&data[idx])) // if the function returns non-zero value 
			idx++;
		else
			idx--;
		}
	}

 }
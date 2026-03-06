#!/usr/bin/env python

import csv,operator,os.path, time,json
from decimal import *

#acc data

for filename in os.listdir("."):
	if filename.startswith("ANDACCX"):
		os.rename(filename,"acc_ax.csv")
	elif filename.startswith("ANDACCY"):
		os.rename(filename,"acc_ay.csv")
	elif filename.startswith("ANDACCZ"):
		os.rename(filename,"acc_az.csv")

		

frp_acc = open('acc_ax.csv', 'rb')
in1fp_acc=open('acc_ay.csv', 'rb')
in2fp_acc=open('acc_az.csv', 'rb')
merged_rows_acc = csv.reader(frp_acc)
data_rows1_acc = csv.reader(in1fp_acc)
data_rows2_acc = csv.reader(in2fp_acc)
final_data_acc = []
row_count=0
hours=0
minutes=0
seconds=0
miliseconds=0
getcontext().prec = 8

for row in merged_rows_acc:
	hours, minutes, seconds = (["0", "0"] + row[1].split(":"))[-3:]
	hours = int(hours)
	minutes = int(minutes)
	seconds = float(seconds)
	#print hours,minutes,seconds
	miliseconds = int(3600000 * hours + 60000 * minutes + 1000 * seconds)
	row[1]=Decimal(miliseconds)/Decimal(86400000)
	#print row[1]
	final_data_acc.append(row)
	row_count += 1

new_data1_acc = []
new_data2_acc=[]
for row in data_rows1_acc:
	new_data1_acc.append(row[2])

for row in data_rows2_acc:
	new_data2_acc.append(row[2])


fwp_acc= open('./MERGED_DATA_acc.csv', 'wb')
csv_writer = csv.writer(fwp_acc, delimiter=',')
for b in range(0, row_count):
	data_acc = []
	for item in final_data_acc[b]:
		data_acc.append(item)
	data_acc.append(new_data1_acc[b])
	data_acc.append(new_data2_acc[b])
	csv_writer.writerow(data_acc)

in1fp_acc.close()
frp_acc.close()
in2fp_acc.close()
fwp_acc.close()
#end acc data

#begin ang data
for filename in os.listdir("."):
	if filename.startswith("ANDORIAZ"):
		os.rename(filename,"ang_az.csv")
	elif filename.startswith("ANDORIPI"):
		os.rename(filename,"ang_pi.csv")
	elif filename.startswith("ANDORIRO"):
		os.rename(filename,"ang_ro.csv")

frp_ang= open('ang_az.csv', 'rb')
in1fp_ang=open('ang_pi.csv', 'rb')
in2fp_ang=open('ang_ro.csv', 'rb')
merged_rows_ang = csv.reader(frp_ang)
data_rows1_ang = csv.reader(in1fp_ang)
data_rows2_ang = csv.reader(in2fp_ang)
final_data_ang = []
row_count=0
hours=0
minutes=0
seconds=0
miliseconds=0
getcontext().prec = 8

for row in merged_rows_ang:
	hours, minutes, seconds = (["0", "0"] + row[1].split(":"))[-3:]
	hours = int(hours)
	minutes = int(minutes)
	seconds = float(seconds)
	#print hours,minutes,seconds
	miliseconds = int(3600000 * hours + 60000 * minutes + 1000 * seconds)
	row[1]=Decimal(miliseconds)/Decimal(86400000)
	#print row[1]
	final_data_ang.append(row)
	row_count += 1

new_data1_ang = []
new_data2_ang=[]
for row in data_rows1_ang:
	new_data1_ang.append(row[2])

for row in data_rows2_ang:
	new_data2_ang.append(row[2])


fwp_ang= open('./MERGED_DATA_ang.csv', 'wb')
csv_writer = csv.writer(fwp_ang, delimiter=',')
for b in range(0, row_count):
	data_ang = []
	for item in final_data_ang[b]:
		data_ang.append(item)
	data_ang.append(new_data1_ang[b])
	data_ang.append(new_data2_ang[b])
	csv_writer.writerow(data_ang)

in1fp_ang.close()
frp_ang.close()
in2fp_ang.close()
fwp_ang.close()
#end ang data

#begin gps data
for filename in os.listdir("."):
	if filename.startswith("ANDGPSLA"):
		os.rename(filename,"gps_lat.csv")
	elif filename.startswith("ANDGPSLO"):
		os.rename(filename,"gps_lon.csv")
	elif filename.startswith("ANDGPSSP"):
		os.rename(filename,"gps_sp.csv")

frp_gps = open('./gps_lat.csv', 'rb')
in1fp_gps=open('./gps_lon.csv', 'rb')
in2fp_gps=open('./gps_sp.csv', 'rb')
merged_rows_gps = csv.reader(frp_gps)
data_rows1_gps = csv.reader(in1fp_gps)
data_rows2_gps = csv.reader(in2fp_gps)
final_data_gps = []
row_count=0
hours=0
minutes=0
seconds=0
miliseconds=0
getcontext().prec = 8

for row in merged_rows_gps:
	hours, minutes, seconds = (["0", "0"] + row[1].split(":"))[-3:]
	hours = int(hours)
	minutes = int(minutes)
	seconds = float(seconds)
	#print hours,minutes,seconds
	miliseconds = int(3600000 * hours + 60000 * minutes + 1000 * seconds)
	row[1]=Decimal(miliseconds)/Decimal(86400000)
	#print row[1]
	final_data_gps.append(row)
	row_count += 1

new_data1_gps = []
new_data2_gps=[]
for row in data_rows1_gps:
	new_data1_gps.append(row[2])

for row in data_rows2_gps:
	new_data2_gps.append(row[2])


fwp_gps= open('./MERGED_DATA_gps.csv', 'wb')
csv_writer = csv.writer(fwp_gps, delimiter=',')
for b in range(0, row_count):
	data_gps = []
	for item in final_data_gps[b]:
		data_gps.append(item)
	data_gps.append(new_data1_gps[b])
	data_gps.append(new_data2_gps[b])
	csv_writer.writerow(data_gps)

in1fp_gps.close()
frp_gps.close()
in2fp_gps.close()
fwp_gps.close()

#end gps data
##
###begin image data
##
##for filename in os.listdir("."):
##	if filename.startswith("CAMPIC"):
##		os.rename(filename,"cam.csv")
##
##frp_img = open('./cam.csv','rb')
##merged_rows_img = csv.reader(frp_img)
##final_data_img = []
##row_count=0
##hours=0
##minutes=0
##seconds=0
##miliseconds=0
##getcontext().prec = 8
##
##for row in merged_rows_img:
##	hours, minutes, seconds = (["0", "0"] + row[1].split(":"))[-3:]
##	hours = int(hours)
##	minutes = int(minutes)
##	seconds = float(seconds)
##	miliseconds = int(3600000 * hours + 60000 * minutes + 1000 * seconds)
##	row[1]=Decimal(miliseconds)/Decimal(86400000)
##	row.append(0)
##	row.append(0)
##	final_data_img.append(row)
##	row_count += 1
##
##fwp_img = open('MERGED_DATA_cam.csv', 'wb')
##csv_writer = csv.writer(fwp_img, delimiter=',')
##for row in final_data_img:
##	csv_writer.writerow(row)
##
##frp_img.close()
##fwp_img.close()
###end image data
	
#begin final data merging
accfp = open('MERGED_DATA_acc.csv', 'rb')
gpsfp = open('MERGED_DATA_gps.csv', 'rb')
anfp = open('MERGED_DATA_ang.csv', 'rb')
##imgfp=open('MERGED_DATA_cam.csv','rb')

acc= csv.reader(accfp)
gps= csv.reader(gpsfp)
an= csv.reader(anfp)
##images=csv.reader(imgfp)

#lists for flag appending(to be used for sorting)
data=[]
acc_data=[]
an_data=[]
gps_data=[]
img_data=[]
i=0# some loop variable

getcontext().prec = 8
#begin appending flags
for row in acc:
	row.append('acc')
	acc_data.append(row)

for row in gps:
	row.append('gps')
	gps_data.append(row)

for row in an:
	row.append('an')
	an_data.append(row)

##for row in images:
##	row.append('img')
##	img_data.append(row)

#end appending flags

#begin merge all data into one
for row in acc_data:
	data.append(row)


for row in gps_data:
	data.append(row)

for row in an_data:
	data.append(row)
##for row in img_data:
##	data.append(row)

#end merge all data

#begin sort all data

data_sort=[]
data_sort=sorted(data, key=operator.itemgetter(0, 1))
'''
for row in data_sort:
	print row
	print '\n'
'''
#end sorting of data


#variables for writing data into file

x=0
y=0
z=0
lat=0
lon=0
sp=0
azi=0
p=0
r=0
final_data=[]
j=0
cnt=0
for row in data_sort:
	#print row
	if row[5]=='acc':
		x=row[2]
		y=row[3]
		z=row[4]
	elif row[5]=='gps':
		lat=row[2]
		lon=row[3]
		sp=row[4]
	elif row[5]=='an':
		azi=row[2]
		p=row[3]
		r=row[4]
	elif row[5]=='img':
		cnt+=1
	row.extend([x,y,z,lat,lon,sp,azi,p,r,cnt])
	final_data.append(row)
	j+=1
	
print j

#for row in final_data:
#	print row
#	print '\n'


for row in final_data:
	del row[2]
	del row[2]
	del row[2]
	del row[2]
	del row[0]


with open('FINAL_DATA.txt','w') as myfile:
    for t in final_data:
  	myfile.write(' '.join(str(s) for s in t) + '\n')


filePath = os.curdir
fileCount = 1;
for root, dirs, files in os.walk(filePath):
   for filename in files:
       if(filename.endswith(".jpg")):
           os.rename(os.path.join(root, filename),os.path.join(root,"IMG_"+str(fileCount)+".jpg"))
           fileCount = fileCount +1
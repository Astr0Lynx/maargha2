- The files are divided into code and data folders
- Data contains all the raw unprocessed data from the trips
- Code contains different parts:
    - Android app - this is the data collection app which is written in Android
        - It can be run using Android studio
        - The app requires OpenCV app as a prerequisite on phone to run

    - Maarg App - this is the data processing and DAV subsystem
        - You can run the react part of the app after installing the node packages
        - For doing the amalgamation, you need to divide the data into smaller segments (2 meter x 2 meter), store those in a file -> then perform amalgamation using the algorithm written in the thesis
        - For proceesing using knn, use the project highway system which is written in c++

- If any part of the code is not clear, you can refer to the thesis doc for clear understanding, it contains the differnt steps performed to arrive at the final result

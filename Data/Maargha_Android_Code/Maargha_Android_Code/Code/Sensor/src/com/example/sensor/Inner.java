package com.example.sensor;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Timer;
import java.util.TimerTask;

import org.apache.http.HttpResponse;
import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.impl.client.DefaultHttpClient;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;



import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.database.sqlite.SQLiteDatabase;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Picture;
import android.hardware.Camera;
import android.hardware.Camera.PictureCallback;
import android.hardware.Camera.ShutterCallback;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.location.OnNmeaMessageListener;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.os.CountDownTimer;
import android.os.Environment;
import android.os.StrictMode;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.view.SurfaceView;
import android.view.View;
import android.webkit.WebChromeClient.CustomViewCallback;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;



public class Inner extends Activity implements LocationListener {

	SensorManager sm = null;  
    TextView textView1 = null;  
    List list,list1;
    SimpleDateFormat date;
    String format,latitude="",longitude="",speed="";
    TextView textTimeLeft;
    protected LocationManager locationManager;
    Sensor sensor2;
    Location location;
    protected LocationListener locationListener;
    int ACCEL_SENSOR_DELAY=1000;
    long lastAccelSensorChange = 0;
    float[] values1,values2={0,0,0};
    DatabaseAdapter database;
    ImageView imageView;
    String mCurrentPhotoPath;
    Preview preview;
    String TAG = "Sensor";
    String loc = null;
    TextView t1,t2;
    String time="";
    String acc,cam;
    int camfreq=2000;
    EditText et1;
    String file;
    // Phase 2 Implementation: Native NMEA Logging
    FileOutputStream nmeaFileStream;
    OnNmeaMessageListener nmeaListener;
    
    // Live UI Telemetry State
    String liveAccel = "ACCEL: Waiting...";
    String liveGps = "GPS: Waiting...";
    String liveNmea = "NMEA: Waiting...";

    private void updateTelemetryUI() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (t1 != null) {
                    t1.setText(liveAccel + "\n\n" + liveGps + "\n" + liveNmea);
                }
            }
        });
    }
 
	@Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        // Dynamically morph the START button into a STOP button!
        Button startBtn = (Button) findViewById(R.id.button1);
        if (startBtn != null) {
            startBtn.setText("STOP LOGGING");
            startBtn.setBackgroundTintList(android.content.res.ColorStateList.valueOf(android.graphics.Color.parseColor("#EF4444"))); 
            startBtn.setOnClickListener(new View.OnClickListener() {
                @Override
                public void onClick(View v) {
                    Intent intent = new Intent(Inner.this, MainActivity.class);
                    intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
                    startActivity(intent);
                    finish(); // Safely triggers onDestroy() to drop NMEA hooks
                }
            });
        }

        t1 = (TextView)findViewById(R.id.textView1);
        et1 = (EditText)findViewById(R.id.editText1);
        imageView = (ImageView)findViewById(R.id.imageView1);
        Bundle b = getIntent().getExtras();
		if(b!=null)
		{
			acc = (String)b.getString("acc");
			cam = (String)b.getString("cam");
			
		}
		Log.d("name",acc+"s"+cam);
	//	Toast.makeText(this, acc+"s"+camfreq, Toast.LENGTH_SHORT).show();
		if(acc!=null)
		ACCEL_SENSOR_DELAY = (int)Float.parseFloat(acc);
		if(cam!=null)
		camfreq = (int)Float.parseFloat(cam);
		// Silenced 2014 debug toast
		
    //    t2 = (TextView)findViewById(R.id.textView2);
        date  = new SimpleDateFormat("hh-mm-ss");
       
        database = new DatabaseAdapter(this);
        
        // Phase 2 Fix: Auto-trigger the tracking hardware instantly without requiring a second click!
        Start(null);
}
	
	public void ViewData(View v)
	{
		Intent i2 = new Intent(this,Data.class);
		startActivity(i2);
	}
	public void Settings(View v)
	{
		Intent i = new Intent(this,Settings.class);
		i.putExtra("boolean","true");
		startActivity(i);
	}
	   public void Start(View v)
	   {
		  file = et1.getText().toString();
		  
		  // Phase 2 Implementation: Create a background sync stream to record NMEA
		  try {
		      File dir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
		      if (!dir.exists()) dir.mkdirs();
		      String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
		      File nmeaFile = new File(dir, "Maargha_Raw_NMEA_" + timeStamp + ".txt");
		      nmeaFileStream = new FileOutputStream(nmeaFile, true);
		  } catch (Exception e) {
		      e.printStackTrace();
		  }

		  preview = new Preview(this);
	        ((FrameLayout) findViewById(R.id.preview)).addView(preview);
		  locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);    
	        locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 0, 0,this );
            
	        // Phase 2 Implementation: Async Hardware NMEA String Interceptor
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                nmeaListener = new OnNmeaMessageListener() {
                    @Override
                    public void onNmeaMessage(String message, long timestamp) {
                        try {
                            if (nmeaFileStream != null) {
                                nmeaFileStream.write(message.getBytes());
                            }
                            String cleanMsg = message.trim();
                            if(cleanMsg.length() > 28) cleanMsg = cleanMsg.substring(0, 28) + "...";
                            liveNmea = "RAW NMEA: " + cleanMsg;
                            updateTelemetryUI();
                        } catch (IOException e) { e.printStackTrace(); }
                    }
                };
                try {
                	locationManager.addNmeaListener(nmeaListener, null);
                } catch(SecurityException e) { e.printStackTrace(); }
            }
	     //  database.deleteContact("abhi");
	         JsonReadTask1 task1 = new JsonReadTask1();
	     	  task1.execute();
	     	 JsonReadTask2 task2 = new JsonReadTask2();
	    	  task2.execute();
	    	  JsonReadTask3 task3 = new JsonReadTask3();
	     	  task3.execute();
		  
	   }
	   
	   @Override
	    public void onProviderDisabled(String provider)
	    {
	      Toast.makeText( getApplicationContext(), "Gps Disabled", Toast.LENGTH_SHORT ).show();
	    }

	    @Override
	    public void onProviderEnabled(String provider)
	    {
	      Toast.makeText( getApplicationContext(), "Gps Enabled", Toast.LENGTH_SHORT).show();
	    }

	    @Override
	    public void onStatusChanged(String provider, int status, Bundle extras)
	    {

	    }
	    @Override
	    public void onLocationChanged(Location location) {
	    //	txtLat = (TextView) findViewById(R.id.textview1);
	    //	txtLat.setText("Latitude:" + location.getLatitude() + ", Longitude:" + location.getLongitude());
	    	Log.d("map3","7");
	    	latitude = location.getLatitude()+"";
	    	longitude = location.getLongitude()+"";
	    	speed = location.getSpeed()+"";
            liveGps = String.format("LAT: %.5f | LON: %.5f", location.getLatitude(), location.getLongitude());
            updateTelemetryUI();
	    //	Toast.makeText(this, latitude+"a"+longitude, Toast.LENGTH_SHORT).show();
	    
	    }
	   
	   
	   


     private class JsonReadTask1 extends AsyncTask<String, Void, String> { 
    	 @Override
   	  protected String doInBackground(String... params) {
    		 sm = (SensorManager)getSystemService(SENSOR_SERVICE); 
             textView1 = (TextView)findViewById(R.id.textView1);  
             list = sm.getSensorList(Sensor.TYPE_ACCELEROMETER);
             if(list.size()>0){
                 sm.registerListener(sel, (Sensor) list.get(0), SensorManager.SENSOR_DELAY_GAME);  
             }else{  
                 Toast.makeText(getBaseContext(), "Error: No Accelerometer.", Toast.LENGTH_LONG).show();  
             }
    		 return null;
   	  }
   	 
   	 public void accessWebService1() {
   	  JsonReadTask1 task = new JsonReadTask1();
   	  // passes values for the urls string array
   	  task.execute();
   	 }
   	SensorEventListener sel = new SensorEventListener(){  
        public void onAccuracyChanged(Sensor sensor, int accuracy) {}  
        public void onSensorChanged(SensorEvent event) {  	
        	format = date.format(new Date());
        	long now = System.currentTimeMillis();
            if (now-ACCEL_SENSOR_DELAY > lastAccelSensorChange) {
                lastAccelSensorChange = now;
                values1 = event.values.clone();
            database.insertData(values1[0]+"", values1[1]+"", values1[2]+"",speed, latitude, longitude,format,loc,file);
            Log.d("here","here");
            }
            liveAccel = String.format("ACCEL (m/s2)\nX: %05.2f | Y: %05.2f | Z: %05.2f", values1[0], values1[1], values1[2]);
            updateTelemetryUI();
            
        }  
    };  
    
    
    
     }
     
     private class JsonReadTask2 extends AsyncTask<String, Void, String> implements LocationListener { 
    	 @Override
   	  protected String doInBackground(String... params) {
    	//	 locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);    
    	 //       locationManager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 0, 0,this);
    	        
    	        
    	        
    	        try
    	        {
    	        	StrictMode.ThreadPolicy policy = new StrictMode.ThreadPolicy.Builder().permitAll().build();
    		        StrictMode.setThreadPolicy(policy);
    		        location = getLastLocation();
    		        latitude = location.getLatitude()+"";
    		        longitude = location.getLongitude()+"";
    		        speed = location.getSpeed()+"";
    	        }
    	        catch(Exception e)
    	        {
    	        	e.printStackTrace();
    	        }
    		 return null;
   	  }
   	 
   	 public void accessWebService2() {
   	  JsonReadTask2 task = new JsonReadTask2();
   	  // passes values for the urls string array
   	  task.execute();
   	 }
   	 
   	@Override
    public void onLocationChanged(Location location) {
    //	txtLat = (TextView) findViewById(R.id.textview1);
    //	txtLat.setText("Latitude:" + location.getLatitude() + ", Longitude:" + location.getLongitude());
    	Log.d("map3","7");
    	latitude = location.getLatitude()+"";
    	longitude = location.getLongitude()+"";
    	speed = location.getSpeed()+"";
        liveGps = String.format("LAT: %.5f | LON: %.5f", location.getLatitude(), location.getLongitude());
        updateTelemetryUI();
    //	Toast.makeText(this, latitude+"a"+longitude, Toast.LENGTH_SHORT).show();
    
    }
 @Override
    public void onProviderDisabled(String provider)
    {
      Toast.makeText( getApplicationContext(), "Gps Disabled", Toast.LENGTH_SHORT ).show();
    }

    @Override
    public void onProviderEnabled(String provider)
    {
      Toast.makeText( getApplicationContext(), "Gps Enabled", Toast.LENGTH_SHORT).show();
    }

    @Override
    public void onStatusChanged(String provider, int status, Bundle extras)
    {

    }
    private Location getLastLocation() {
        locationManager = (LocationManager)getApplicationContext().getSystemService(LOCATION_SERVICE);
        List<String> providers = locationManager.getProviders(true);
        Location bestLocation = null;
        for (String provider : providers) {
            Location l = locationManager.getLastKnownLocation(provider);
            if (l == null) {
                continue;
            }
            if (bestLocation == null || l.getAccuracy() < bestLocation.getAccuracy()) {
                // Found best last known location: %s", l);
                bestLocation = l;
            }
        }
        return bestLocation;
    }
   	 }
     
     
     
     private class JsonReadTask3 extends AsyncTask<String, Void, String> { 
    	 @Override
   	  protected String doInBackground(String... params) {

    		 	Log.d("cam","1");
    	        Timer timer = new Timer();
    	        Log.d("cam","1.2");
    	        timer.scheduleAtFixedRate( new TimerTask() {
    	        	
    	            public void run() {
    	                  try{
    	                	  Log.d("cam","1.4");
    	                	  preview.camera.takePicture(shutterCallback, rawCallback,
    	                              jpegCallback);
    	                	  Log.d("cam","1.6");
    	                  }
    	                  catch (Exception e) {
    	                      e.printStackTrace();
    	                  }
    	             }
    	            }, 0, 2000); 
    		Log.d("cam","2");
    		 return null;
   	  }
   	 
   	 public void accessWebService3() {
   	  JsonReadTask3 task = new JsonReadTask3();
   	  // passes values for the urls string array
   	  task.execute();
   	 }
   	 
   	ShutterCallback shutterCallback = new ShutterCallback() {
        public void onShutter() {
              Log.d(TAG, "onShutter'd");
        }
  };

  /** Handles data for raw picture */
  PictureCallback rawCallback = new PictureCallback() {
        public void onPictureTaken(byte[] data, Camera camera) {
              Log.d(TAG, "onPictureTaken - raw");
        }
  };

  /** Handles data for jpeg picture */
  PictureCallback jpegCallback = new PictureCallback() {
        public void onPictureTaken(byte[] data, Camera camera) {
        	
        	
        	Log.d("cam","2.2");
        	 String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
      	    String imageFileName = "JPEG_" + timeStamp + "_";
      	    File storageDir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
      	    File image=null;
			try {
				Log.d("cam","2.4");
				image = File.createTempFile(
				    imageFileName,  /* prefix */
				    ".jpg",         /* suffix */
				    storageDir      /* directory */
				   
						);
				 Log.d("cam","2.6");
			} catch (IOException e1) {
				// TODO Auto-generated catch block
				e1.printStackTrace();
			}
      	    
			 Log.d("cam","2.8");
      	    // Save a file: path for use with ACTION_VIEW intents
      	    mCurrentPhotoPath = 	image.getAbsolutePath();
      	    
      	    Log.d("name",mCurrentPhotoPath);
      	    time = mCurrentPhotoPath;
      	  Log.d("cam","3");
        	
        	
        	
        	File f = new File(mCurrentPhotoPath);
            Uri imageFileUri =
            		Uri.fromFile(f);
        	
        	Log.d("here","1");
        		//	getContentResolver().insert(Media.EXTERNAL_CONTENT_URI, new ContentValues());
        	
        	
        	try {
        		Log.d("uri",imageFileUri+"");
        			OutputStream imageFileOS =
        			getContentResolver().openOutputStream(imageFileUri);
        			imageFileOS.write(data);
        			imageFileOS.flush();
        			imageFileOS.close();
        			loc = imageFileUri.toString();
        			imageView.setImageURI(imageFileUri);
        			
        			} catch (FileNotFoundException e) {
        	//		Toast t = Toast.makeText(this,e.getMessage(), Toast.LENGTH_SHORT);
        		//	t.show();
        			} catch (IOException e) {
        	//		Toast t = Toast.makeText(this,e.getMessage(), Toast.LENGTH_SHORT);
        		//	t.show();
        			}
        			camera.startPreview();
       
        }
  };
  
  private File createImageFile() throws IOException {
 	    // Create an image file name
 	    String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
 	    String imageFileName = "JPEG_" + timeStamp + "_";
 	    File storageDir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
 	    File image = File.createTempFile(
 	        imageFileName,  /* prefix */
 	        ".jpg",         /* suffix */
 	        storageDir      /* directory */
 	    );
 	    

 	    // Save a file: path for use with ACTION_VIEW intents
 	    mCurrentPhotoPath = 	image.getAbsolutePath();
 	    Log.d("name",mCurrentPhotoPath);
 	    time = mCurrentPhotoPath;
 	    return image;
 	}
   	 
   	 }
     
    // Phase 2 Implementation: Secure Teardown Pipeline
    @Override
    protected void onDestroy() {
        super.onDestroy();
        try {
            if (nmeaListener != null && locationManager != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                locationManager.removeNmeaListener(nmeaListener);
            }
            if (nmeaFileStream != null) {
                nmeaFileStream.flush();
                nmeaFileStream.close();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}


		
	    
	    
	    




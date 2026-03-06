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



import android.support.v7.app.ActionBarActivity;
import android.text.Editable;
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
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;



public class Settings extends ActionBarActivity {

	EditText et1,et2;
	String cam="0.5",acc="1";
	DatabaseAdapter database;
	String condition;
	CheckBox cb1,cb2,cb3,cb4;
	
	@Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);
        cb1 = (CheckBox)findViewById(R.id.checkBox1);
        cb2 = (CheckBox)findViewById(R.id.checkBox2);
        cb3 = (CheckBox)findViewById(R.id.checkBox3);
        cb4 = (CheckBox)findViewById(R.id.checkBox4);
        database = new DatabaseAdapter(this);
        et1 = (EditText)findViewById(R.id.editText1);
        et2 = (EditText)findViewById(R.id.editText2);
        et1.setText(acc);
        et2.setText(cam);
        Bundle b = getIntent().getExtras();
		if(b!=null)
		{
			condition = (String)b.getString("boolean");
			if(condition.equals("false"))
			{
				acc = et1.getText().toString();
				cam = et2.getText().toString();
				if(cam.equals("")||acc.equals(""))
					Toast.makeText(this, "Fields should not be empty.", Toast.LENGTH_SHORT).show();
				else
				{
					Intent i1 = new Intent(this,Inner.class);
					float v1 = Float.parseFloat(acc);
					float v2 = Float.parseFloat(cam);
					String str1="",str2="";
					Toast.makeText(this,v1+"s"+v2,Toast.LENGTH_LONG).show();
					if(cb1.isChecked())
						str1 = 1000/v1+"";
					else
						str1 = null;
					if(cb2.isChecked())
						str2 = 1000/v2 + "";
					else
						str2 = null;
					i1.putExtra("acc",1000/v1+"");
					i1.putExtra("cam",1000/v2 + "");
					Log.d("name",str1+"s"+str2);
					startActivity(i1);
				}
			}
		}
	}
	public void ChangeAcc(View v)
	{
		acc = et1.getText().toString();
		if(acc.equals(""))
			Toast.makeText(this, "Field cannot be empty.", Toast.LENGTH_SHORT).show();
		else if(!isInt(acc))
		{
			Toast.makeText(this, "Field should only be integer.", Toast.LENGTH_SHORT).show();
			et1.setText("");
			acc = "";
		}	
		else
			acc = et1.getText().toString();
	}
	public void DefAcc(View v)
	{
		et1.setText("1");
		acc = "1000";
	}
	public void ChangeCam(View v)
	{
		cam = et2.getText().toString();
		if(cam.equals(""))
			Toast.makeText(this, "Field cannot be empty.", Toast.LENGTH_SHORT).show();
		else if(!isInt(cam))
		{
			Toast.makeText(this, "Field should only be integer.", Toast.LENGTH_SHORT).show();
			et2.setText("");
			cam="";
		}	
		else
			cam = et2.getText().toString();
	}
	public void DefCam(View v)
	{
		et2.setText("0.5");
		cam = "0.5";
	}
	public boolean isInt(String str)
	{
		for(int i=0;i<str.length();i++)
		{
			char c = str.charAt(i);
			if(c!='1'&&c!='2'&&c!='3'&&c!='4'&&c!='5'&&c!='6'&&c!='7'&&c!='8'&&c!='9'&&c!='0'&&c!='.')
				return false;
		}
		return true;
	}
	
	
	
}
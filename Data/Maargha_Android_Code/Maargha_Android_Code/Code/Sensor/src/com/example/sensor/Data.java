package com.example.sensor;

import java.io.File;
import java.util.ArrayList;
import java.util.HashSet;

import android.app.Activity;
import android.content.DialogInterface.OnClickListener;
import android.content.Intent;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.util.Log;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.view.View.OnLongClickListener;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

public class Data extends Activity implements android.view.View.OnClickListener,OnLongClickListener{

	TextView t;
	DatabaseAdapter database;
	LinearLayout layout;
	Button addButton;
	String file;
	String files[];
	String uri;
	String uris1[];
	String uris[];
	String files1[];
	ImageView img;
	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		setContentView(R.layout.activity_data);
		database = new DatabaseAdapter(this);
		img = (ImageView)findViewById(R.id.imageView1);
		layout  = (LinearLayout)findViewById(R.id.layout1);
		ArrayList<String> files1 = new ArrayList<String>();
		file = database.getAllFiles();
		int sum=0;
		for(int i=0;i<file.length();i++)
		{
			if(file.charAt(i)=='*')
				sum++;
		}
		int j=0;
		files = new String[sum+2];
		for(int i=0;i<sum;i++)
		{
			files[i]="";
		}
		for(int i=0;i<file.length()-1;i++)
		{
			if(file.charAt(i)!='*')
			{
				files[j] = files[j]+file.charAt(i);
			}	
			else if(file.charAt(i)=='*')
				j++;
		}
		for(int k=0;k<j;k++)
		{
			files1.add(files[k]);
		}
		HashSet hs = new HashSet();
        hs.addAll(files1);
        files1.clear();
        files1.addAll(hs);
	//	Toast.makeText(this, files1.get(1), Toast.LENGTH_SHORT).show();
		for(int i=0;i<files1.size();i++)
		{
		addButton =new Button(this);
		layout.addView(addButton);
		addButton.setText(files1.get(i));
		addButton.setClickable(true);
		addButton.setOnClickListener(this);
		addButton.setOnLongClickListener(this);
		}
		
			
	}
	public void onClick(View v)
	{
		Button b = (Button)v;
        String name = b.getText().toString();
  //      Toast.makeText(this, database.getUriFromFile(name), Toast.LENGTH_LONG).show();
		Intent i = new Intent(this,DataView.class);
		i.putExtra("name", name);
		startActivity(i);
	}
	public boolean onLongClick(View v)
	{
		Button b = (Button)v;
        String name = b.getText().toString();
        Log.d("long","0");
		ArrayList<String> uris1 = new ArrayList<String>();
		Log.d("long","1");
		String uri = database.getUriFromFile(name);
		int sum=0;
		for(int i=0;i<uri.length();i++)
		{
			if(uri.charAt(i)=='*')
				sum++;
		}
		int j=0;
	//	Toast.makeText(this,uri,Toast.LENGTH_LONG).show();
	//	Toast.makeText(this,uri,Toast.LENGTH_LONG).show();
		uris = new String[sum+2];
		for(int i=0;i<sum;i++)
		{
			uris[i]="";
		}
		for(int i=0;i<uri.length()-1;i++)
		{
			if(uri.charAt(i)!='*')
			{
				uris[j] = uris[j]+uri.charAt(i);
			}	
			else if(uri.charAt(i)=='*')
				j++;
		}
		Log.d("excep",j+"");
		uris1.clear();
		for(int k=0;k<j;k++)
		{
			uris1.add(uris[k]);
		}
		StringBuffer buffer = new StringBuffer();
		for(int i=0;i<uris1.size();i++)
		{
			buffer.append(uris1.get(i)+"\n");
		}
		String str = buffer.toString();
		
		Log.d("excep",uris1.size()+"");
		HashSet hs = new HashSet();
        hs.addAll(uris1);
        uris1.clear();
        uris1.addAll(hs);
        for(int l=0;l<uris1.size();l++)
        {
        	File file= new File(uris1.get(l));
            if(file.exists())
            {
                 file.delete();
            }
        }
        database.deleteContact(name);
        Intent i = new Intent(this,Data.class);
        startActivity(i); 
        return true;
	}

}

package com.example.sensor;

import com.example.sensor.DatabaseAdapter.DatabaseHelper;

import android.app.Activity;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.TextView;

public class DataDelete extends Activity {

	DatabaseAdapter database;
	TextView t;
	
	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		setContentView(R.layout.activity_data_delete);
		database = new DatabaseAdapter(this);
		t = (TextView)findViewById(R.id.textView1);
		t.setText(database.getAllData());
		
	}

	
}

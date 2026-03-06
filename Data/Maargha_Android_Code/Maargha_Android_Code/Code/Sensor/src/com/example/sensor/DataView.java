package com.example.sensor;



import android.support.v7.app.ActionBarActivity;
import android.os.Bundle;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.TableLayout;
import android.widget.TextView;

public class DataView extends ActionBarActivity {
	
	String file;
	DatabaseAdapter database;
	TextView t;

	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		setContentView(R.layout.activity_data_view);
		t = (TextView)findViewById(R.id.textView1);
		database = new DatabaseAdapter(this);
		Bundle b = getIntent().getExtras();
		if(b!=null)
		{
			file = (String)b.getString("name");
		}
		t.setText(database.getDataFromFile(file));
	
	}
}

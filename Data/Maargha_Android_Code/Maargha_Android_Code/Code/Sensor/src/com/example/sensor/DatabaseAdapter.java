package com.example.sensor;

import java.nio.ByteBuffer;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.SQLException;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteDatabase.CursorFactory;
import android.database.sqlite.SQLiteOpenHelper;
import android.graphics.Bitmap;
import android.util.Log;
import android.widget.Toast;


public class DatabaseAdapter
{
	DatabaseHelper helper;
	public DatabaseAdapter(Context context)
	{
		helper = new DatabaseHelper(context);
	}
	public boolean insertData(String x, String y,String z,String speed,String latitude,String longitude,String time,String loc,String file)
	{
		
    	Log.d("db","1");
		SQLiteDatabase db1 = helper.getWritableDatabase();
		Log.d("db","2");
		String[] columns = {DatabaseHelper.UID,DatabaseHelper.NAME1,DatabaseHelper.NAME2,DatabaseHelper.NAME3,DatabaseHelper.SPEED,DatabaseHelper.LATITUDE,DatabaseHelper.LONGITUDE,DatabaseHelper.TIME,DatabaseHelper.LOCATION,DatabaseHelper.FILE};
		Log.d("db","3");
		Cursor cursor =  db1.query(DatabaseHelper.TABLE_NAME, columns, null, null, null, null, null);
		Log.d("db","4");
	/*	while(cursor.moveToNext())
		{
			Log.d("db","5");
			//int index1 = cursor.getColumnIndex(DatabaseOperations.UID);
		//	int cid = cursor.getInt(0);
		//	String id = cursor.getString(0)
		//	Log.d("db","6"+pass);
			String name1 = cursor.getString(1);
			String password1 = cursor.getString(2);
			Log.d("db","7"+name);
			//int num = Integer.parseInt(cursor.getString(3)); 
			if(name1.equals(name))
			{
				return true;
			}
			else
				Log.d("db","9");
			
		}	*/	
		
		SQLiteDatabase db = helper.getWritableDatabase();
		db.beginTransaction();
		ContentValues contentValues = new ContentValues();
		contentValues.put(DatabaseHelper.NAME1, x);
		contentValues.put(DatabaseHelper.NAME2, y);
		contentValues.put(DatabaseHelper.NAME3, z);
		contentValues.put(DatabaseHelper.SPEED, speed);
		contentValues.put(DatabaseHelper.LATITUDE, latitude);
		contentValues.put(DatabaseHelper.LONGITUDE, longitude);
		contentValues.put(DatabaseHelper.TIME, time);
		contentValues.put(DatabaseHelper.LOCATION,loc);
		contentValues.put(DatabaseHelper.FILE, file);
		Log.d("data","here1");
		long id = db.insert(DatabaseHelper.TABLE_NAME,null,contentValues);
		Log.d("data","here2");
		db.setTransactionSuccessful();
		db.endTransaction();
		return false;
	}
	/*public String checkdata(String user,String pass)
	{
        	Log.d("db","1");
			SQLiteDatabase db1 = helper.getWritableDatabase();
			Log.d("db","2");
			String[] columns = {DatabaseHelper.UID,DatabaseHelper.NAME1,DatabaseHelper.NAME2,DatabaseHelper.NAME3,DatabaseHelper.SPEED,DatabaseHelper.LATITUDE,DatabaseHelper.LONGITUDE};
			Log.d("db","3");
			Cursor cursor =  db1.query(DatabaseHelper.TABLE_NAME, columns, null, null, null, null, null);
			Log.d("db","4");
			while(cursor.moveToNext())
			{
				Log.d("db","5");
				//int index1 = cursor.getColumnIndex(DatabaseOperations.UID);
			//	int cid = cursor.getInt(0);
			//	String id = cursor.getString(0)
				Log.d("db","6"+pass);
				String name = cursor.getString(1);
				String password = cursor.getString(2);
				Log.d("db","7"+name);
				//int num = Integer.parseInt(cursor.getString(3)); 
				if(user.equals(name)&&pass.equals(password))
				{
				/*	Log.d("db","8");
					String num = cursor.getString(3);
					int n = Integer.parseInt(num);
					n++;
					String New = n+""; 
					ContentValues contentValues = new ContentValues();
					contentValues.put(DatabaseHelper.NUMBER,New);
					SQLiteDatabase db2 = helper.getWritableDatabase();
					String[] whereArgs = {name};
				//	int count=0;
					db2.update(DatabaseHelper.TABLE_NAME, contentValues, DatabaseHelper.NAME+" =? ", whereArgs);
					String num = cursor.getString(3);
					return num;
				}
				else
					Log.d("db","9");
				
			}
			return "asd";
	}
	*/
	/*public boolean update(String user,String newPass)
	{
        	Log.d("db","1");
			SQLiteDatabase db1 = helper.getWritableDatabase();
			Log.d("db","2");
			String[] columns = {DatabaseHelper.UID,DatabaseHelper.NAME,DatabaseHelper.PASSWORD,DatabaseHelper.NUMBER};
			Log.d("db","3");
			Cursor cursor =  db1.query(DatabaseHelper.TABLE_NAME, columns, null, null, null, null, null);
			Log.d("db","4");
			while(cursor.moveToNext())
			{
				Log.d("db","5");
				//int index1 = cursor.getColumnIndex(DatabaseOperations.UID);
			//	int cid = cursor.getInt(0);
			//	String id = cursor.getString(0)
			//	Log.d("db","6"+pass);
				String name = cursor.getString(1);
				Log.d("db","7"+name);
				//int num = Integer.parseInt(cursor.getString(3)); 
				if(user.equals(name))
				{
					Log.d("db","8");
					ContentValues contentValues = new ContentValues();
					contentValues.put(DatabaseHelper.PASSWORD,newPass);
					SQLiteDatabase db2 = helper.getWritableDatabase();
					String[] whereArgs = {name};
				//	int count=0;
					db2.update(DatabaseHelper.TABLE_NAME, contentValues, DatabaseHelper.NAME+" =? ", whereArgs);
					
					return true;
				}
				else
					Log.d("db","9");
				
			}
			return false;
	} */
	
	public void deleteContact (String file)
	   {
	      SQLiteDatabase db = helper.getWritableDatabase();
	      while(db.delete(DatabaseHelper.TABLE_NAME,DatabaseHelper.FILE+" = ? ",new String[] { file })>0)
	      {
	    	  
	      }
	      return;
	   }
	
	public String getAllFiles()
	{
		Log.d("db","1");
		SQLiteDatabase db = helper.getWritableDatabase();
		Log.d("db","2");
		String[] columns = {DatabaseHelper.UID,DatabaseHelper.NAME1,DatabaseHelper.NAME2,DatabaseHelper.NAME3,DatabaseHelper.SPEED,DatabaseHelper.LATITUDE,DatabaseHelper.LONGITUDE,DatabaseHelper.TIME,DatabaseHelper.LOCATION,DatabaseHelper.FILE};	
		Log.d("db","3");
		Cursor cursor =  db.query(DatabaseHelper.TABLE_NAME, columns, null, null, null, null, null);
		Log.d("db","4");
		StringBuffer buffer = new StringBuffer();
		
		while(cursor.moveToNext())
		{
			String file = cursor.getString(9);
			buffer.append(file+"*");	
		}
		return buffer.toString();
	}

	public String getAllData()
	{
		Log.d("db","1");
		SQLiteDatabase db = helper.getWritableDatabase();
		Log.d("db","2");
		String[] columns = {DatabaseHelper.UID,DatabaseHelper.NAME1,DatabaseHelper.NAME2,DatabaseHelper.NAME3,DatabaseHelper.SPEED,DatabaseHelper.LATITUDE,DatabaseHelper.LONGITUDE,DatabaseHelper.TIME,DatabaseHelper.LOCATION,DatabaseHelper.FILE};	
		Log.d("db","3");
		Cursor cursor =  db.query(DatabaseHelper.TABLE_NAME, columns, null, null, null, null, null);
		Log.d("db","4");
		StringBuffer buffer = new StringBuffer();
		
		while(cursor.moveToNext())
		{
			//int index1 = cursor.getColumnIndex(DatabaseOperations.UID);
			int cid = cursor.getInt(0);
			String x = cursor.getString(1);
			String y = cursor.getString(2);
			String z = cursor.getString(3);
			String speed = cursor.getString(4);
			String latitude = cursor.getString(5);
			String longitude = cursor.getString(6);
			String time = cursor.getString(7);
			String loc = cursor.getString(8);
			String file = cursor.getString(9);
			buffer.append(cid+" "+x+" "+y+" "+ z +" "+speed+" "+ latitude + " " + longitude+ " " + time+" " + loc +" "+file+"\n");	
		}
		return buffer.toString();
	}
	public String getDataFromFile(String str)
	{
		Log.d("db","1");
		SQLiteDatabase db = helper.getWritableDatabase();
		Log.d("db","2");
		String[] columns = {DatabaseHelper.UID,DatabaseHelper.NAME1,DatabaseHelper.NAME2,DatabaseHelper.NAME3,DatabaseHelper.SPEED,DatabaseHelper.LATITUDE,DatabaseHelper.LONGITUDE,DatabaseHelper.TIME,DatabaseHelper.LOCATION,DatabaseHelper.FILE};	
		Log.d("db","3");
		Cursor cursor =  db.query(DatabaseHelper.TABLE_NAME, columns, null, null, null, null, null);
		Log.d("db","4");
		StringBuffer buffer = new StringBuffer();
		
		while(cursor.moveToNext())
		{
			//int index1 = cursor.getColumnIndex(DatabaseOperations.UID);
			int cid = cursor.getInt(0);
			String x = cursor.getString(1);
			String y = cursor.getString(2);
			String z = cursor.getString(3);
			String speed = cursor.getString(4);
			String latitude = cursor.getString(5);
			String longitude = cursor.getString(6);
			String time = cursor.getString(7);
			String loc = cursor.getString(8);
			String file = cursor.getString(9);
			if(file.equals(str))
				buffer.append(cid+" "+x+" "+y+" "+ z +" "+speed+" "+ latitude + " " + longitude+ " " + time+" " + loc +" "+file+"\n");	
		}
		return buffer.toString();
	}
	
	public String getUriFromFile(String str)
	{
		Log.d("db","1");
		SQLiteDatabase db = helper.getWritableDatabase();
		Log.d("db","2");
		String[] columns = {DatabaseHelper.UID,DatabaseHelper.NAME1,DatabaseHelper.NAME2,DatabaseHelper.NAME3,DatabaseHelper.SPEED,DatabaseHelper.LATITUDE,DatabaseHelper.LONGITUDE,DatabaseHelper.TIME,DatabaseHelper.LOCATION,DatabaseHelper.FILE};	
		Log.d("db","3");
		Cursor cursor =  db.query(DatabaseHelper.TABLE_NAME, columns, null, null, null, null, null);
		Log.d("db","4");
		StringBuffer buffer = new StringBuffer();
		
		while(cursor.moveToNext())
		{
			String loc = cursor.getString(8);
			String file = cursor.getString(9);
			if(file.equals(str))
				buffer.append(loc+"*");	
		}
		return buffer.toString();
	}
	
	
	
    static class DatabaseHelper extends SQLiteOpenHelper {
	
	private static final String DATABASE_NAME = "regdatabase22";
	private static final String TABLE_NAME = "regtable22";
	private static final int DATABASE_VERSION = 122;
	private static final String UID = "_id";
	private static final String NAME1 = "Name102";
	private static final String NAME2 = "Name202";
	private static final String NAME3 = "Name302";
	private static final String SPEED = "Speed22";
	private static final String LATITUDE = "Latitude22";
	private static final String LONGITUDE = "Longitude22";
	private static final String TIME = "Time22";
	private static final String LOCATION = "location22";
	private static final String FILE = "file4";
	
	//private static final String CREATE_TABLE = "CREATE TABLE "+TABLE_NAME+" (" + UID + " INTEGER PRIMARY KEY AUTOINCREMENT, "+NAME+");";
	private static final String CREATE_TABLE = "CREATE TABLE "+TABLE_NAME+" (" + UID + " INTEGER PRIMARY KEY AUTOINCREMENT, "+NAME1+" VARCHAR(255), "+NAME2+" VARCHAR(255), "+NAME3+" VARCHAR(255), "+SPEED+" VARCHAR(255), "+LATITUDE+" VARCHAR(255), "+LONGITUDE+" VARCHAR(255), "+TIME+" VARCHAR(255), "+LOCATION+" VARCHAR(255), "+FILE+" VARCHAR(255));";
	private static final String DROP_TABLE = "DROP TABLE IF EXISTS "+ TABLE_NAME;
	private Context context;
	
	
	public DatabaseHelper(Context context)
	{
		super(context, DATABASE_NAME, null, DATABASE_VERSION);
	//	Toast.makeText(context,"constructor called", Toast.LENGTH_SHORT).show();
		// TODO Auto-generated constructor stub
	}

	@Override
	public void onCreate(SQLiteDatabase db) {
		// TODO Auto-generated method stub
		try {
			Log.d("asd","qsd");
			db.execSQL(CREATE_TABLE);
			Log.d("asd","qsd1");
		} catch (SQLException e) {
			// TODO Auto-generated catch block
			Toast.makeText(context,"sqlite error 1", Toast.LENGTH_SHORT).show();
		}
	}

	@Override
	public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
		// TODO Auto-generated method stub
		try {
			Log.d("asd","qsd2");
		//	Toast.makeText(context, "upgrade called", Toast.LENGTH_SHORT).show();
			db.execSQL(DROP_TABLE);
			Log.d("asd","qsd3");
			onCreate(db);
			Log.d("asd","qsd4");
			//Toast.makeText(context,"upgrade finished",Toast.LENGTH_SHORT).show();
		} catch (SQLException e) {
			// TODO Auto-`generated catch block
			Toast.makeText(context, "sqlite error", Toast.LENGTH_SHORT).show();
		}
	}
	

}
}

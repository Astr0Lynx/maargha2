package com.example.sensor;

import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.List;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.hardware.Camera;
import android.hardware.Camera.PreviewCallback;
import android.util.Log;
import android.view.SurfaceHolder;
import android.view.SurfaceView;

public class Preview  extends SurfaceView implements SurfaceHolder.Callback {
                private static final String TAG = "Preview";

                SurfaceHolder mHolder;
                public Camera camera;

                Preview(Context context) {
                                super(context);

                                // Install a SurfaceHolder.Callback so we get notified when the
                                // underlying surface is created and destroyed.
                                mHolder = getHolder();
                                mHolder.addCallback(this);
                                mHolder.setType(SurfaceHolder.SURFACE_TYPE_PUSH_BUFFERS);
                }
                
                public void releaseCameraAndPreview() {
                  //  myCameraPreview.setCamera(null);
                    if (camera != null) {
                        camera.release();
                        camera = null;
                    }
                }
                

                public void surfaceCreated(SurfaceHolder holder) {
                                // The Surface has been created, acquire the camera and tell it where
                                // to draw.
                	try {
                	    releaseCameraAndPreview();
                	    
                	    
                	        camera = Camera.open(Camera.CameraInfo.CAMERA_FACING_BACK);
                	    
                	} catch (Exception e) {
                	    Log.d("camera", "failed to open Camera");
                	    e.printStackTrace();
                	}
                                try {
                                                camera.setPreviewDisplay(holder);

                                                camera.setPreviewCallback(new PreviewCallback() {

                                                                public void onPreviewFrame(byte[] data, Camera arg1) {
//                                                           
                                                                                Preview.this.invalidate();
                                                                }
                                                });
                                } catch (IOException e) {
                                                e.printStackTrace();
                                }
                }

                public void surfaceDestroyed(SurfaceHolder holder) {
                                // Surface will be destroyed when we return, so stop the preview.
                                // Because the CameraDevice object is not a shared resource, it's very
                                // important to release it when the activity is paused.
                                camera.stopPreview();
                                camera = null;
                }

                public void surfaceChanged(SurfaceHolder holder, int format, int w, int h) {
                                // Now that the size is known, set up the camera parameters and begin
                                // the preview.
                	Camera.Parameters parameters = camera.getParameters();
                    List<Camera.Size> previewSizes = parameters.getSupportedPreviewSizes();

                    // You need to choose the most appropriate previewSize for your app
                    Camera.Size previewSize = previewSizes.get(0);
                    		parameters.setPreviewSize(previewSize.width, previewSize.height);
                    camera.setParameters(parameters);
                    camera.startPreview();
                }

}

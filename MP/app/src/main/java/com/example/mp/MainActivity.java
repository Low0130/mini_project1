// MainActivity.java

package com.example.mp;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Bundle;
import android.os.Vibrator;
import android.util.Log;
import android.view.View; // ADDED: Import for View.GONE
import android.view.animation.RotateAnimation;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageAnalysis;
import androidx.camera.core.ImageProxy;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import com.google.common.util.concurrent.ListenableFuture;
import java.nio.ByteBuffer;
import java.util.Locale;
import java.util.Map;

public class MainActivity extends AppCompatActivity implements SensorEventListener {

    private static final String TAG = "MainActivity";
    private static final int CAMERA_PERMISSION_REQUEST_CODE = 101;
    private static final float TOLERANCE_DEGREES = 15f;
    private static final long FEEDBACK_INTERVAL_MS = 1000;

    private ImageView arrowImage;
    private TextView distanceText;
    private PreviewView cameraPreview;
    private TextView statusText;
    private OverlayView overlayView;

    private SensorManager sensorManager;
    private Vibrator vibrator;

    private Python python;
    private PyObject navigationProcessor;

    private String destinationId;
    private boolean isPathPlanned = false;
    private long lastFeedbackTime = 0L;
    private float currentArrowRotation = 0f;
    private final float[] gravity = new float[3];
    private final float[] geomagnetic = new float[3];
    private float targetAzimuth = 0.0f;
    private float targetDistance = 0.0f;

    // ADDED: The new state variable to control the guidance system.
    private boolean hasArrived = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        arrowImage = findViewById(R.id.arrowImage);
        distanceText = findViewById(R.id.distanceText);
        cameraPreview = findViewById(R.id.cameraPreview);
        statusText = findViewById(R.id.statusText);
        overlayView = findViewById(R.id.overlayView);

        initPython();
        if (python != null) {
            navigationProcessor = python.getModule("navigation_logic").callAttr("NavigationProcessor");
        }

        destinationId = getIntent().getStringExtra("DESTINATION_ID");
        if (destinationId == null) {
            Log.e(TAG, "No destination ID was provided.");
            Toast.makeText(this, "Error: No destination selected.", Toast.LENGTH_LONG).show();
            finish();
            return;
        }

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        vibrator = (Vibrator) getSystemService(VIBRATOR_SERVICE);

        String initialMessage = "Please scan the nearest QR code to begin navigation.";
        statusText.setText(initialMessage);
        TTSService.getInstance().speak(initialMessage);

        if (isCameraPermissionGranted()) {
            startCamera();
        } else {
            requestCameraPermission();
        }
    }

    private void initPython() {
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
        python = Python.getInstance();
    }

    private void startCamera() {
        ListenableFuture<ProcessCameraProvider> cameraProviderFuture = ProcessCameraProvider.getInstance(this);
        cameraProviderFuture.addListener(() -> {
            try {
                ProcessCameraProvider cameraProvider = cameraProviderFuture.get();
                Preview preview = new Preview.Builder().build();
                preview.setSurfaceProvider(cameraPreview.getSurfaceProvider());
                CameraSelector cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA;
                ImageAnalysis imageAnalysis = new ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build();

                imageAnalysis.setAnalyzer(ContextCompat.getMainExecutor(this), this::processImageProxy);

                cameraProvider.unbindAll();
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalysis);
            } catch (Exception e) {
                Log.e(TAG, "CameraX binding failed", e);
            }
        }, ContextCompat.getMainExecutor(this));
    }

    private void processImageProxy(ImageProxy imageProxy) {
        try {
            if (navigationProcessor == null || python == null) return;
            // ADDED: Stop processing frames once the user has arrived.
            if (hasArrived) {
                imageProxy.close();
                return;
            }
            byte[] imageData = imageProxyToByteArray(imageProxy);
            if (imageData == null) return;

            PyObject result = navigationProcessor.callAttr("process_camera_frame",
                    imageData, imageProxy.getWidth(), imageProxy.getHeight());

            if (result == null) {
                Log.e(TAG, "Python returned a null result, possibly due to a crash.");
                updateStatus("Python Error. Check Logs.", false);
                return;
            }

            Map<PyObject, PyObject> resultMap = result.asMap();
            PyObject statusKey = python.getBuiltins().get("str").call("status");
            PyObject statusObj = resultMap.get(statusKey);

            if (statusObj == null) {
                Log.e(TAG, "Python result dictionary is missing the 'status' key. Full dict: " + resultMap.toString());
                return;
            }
            String status = statusObj.toString();

            PyObject corners = resultMap.get(python.getBuiltins().get("str").call("corners"));
            if (corners != null) {
                overlayView.setCorners(corners, imageProxy.getWidth(), imageProxy.getHeight());
            } else {
                overlayView.clear();
            }

            switch (status) {
                case "SCANNING":
                    break;
                case "DETECTED":
                    updateStatus("QR Code detected, hold steady.", false);
                    break;
                case "LOCATION_CONFIRMED":
                    handleLocationConfirmed(resultMap);
                    break;
                case "NAVIGATING":
                    handleNavigating(resultMap);
                    break;
                case "ARRIVED":
                    // MODIFIED: Handle the arrival state.
                    updateStatus("You have arrived at your destination!", true);
                    this.hasArrived = true; // Set the flag to stop guidance
                    // Hide UI elements that are no longer needed
                    arrowImage.setVisibility(View.GONE);
                    distanceText.setVisibility(View.GONE);
                    break;
                case "OFF_TRACK_RECALCULATED":
                    updateStatus("Off track. New path calculated.", true);
                    break;
                case "OFF_TRACK_ERROR":
                case "ERROR":
                    PyObject errorObj = resultMap.get(python.getBuiltins().get("str").call("message"));
                    String errorMessage = (errorObj != null) ? errorObj.toString() : "An unknown error occurred.";
                    updateStatus("Error: " + errorMessage, true);
                    break;
            }
        } catch (Exception e) {
            Log.e(TAG, "CRITICAL ERROR in Python call or analyzer loop", e);
        } finally {
            imageProxy.close();
        }
    }

    private void handleLocationConfirmed(Map<PyObject, PyObject> resultMap) {
        PyObject locNameObj = resultMap.get(python.getBuiltins().get("str").call("location_name"));
        String locName = (locNameObj != null) ? locNameObj.toString() : "an unknown location";

        if (!isPathPlanned) {
            updateStatus("Current location confirmed as " + locName + ". Planning route...", true);
            PyObject pathResult = navigationProcessor.callAttr("set_destination", destinationId);
            if (pathResult == null) {
                updateStatus("Error: Failed to plan path.", true);
                return;
            }

            Map<PyObject, PyObject> pathResultMap = pathResult.asMap();
            PyObject pathStatusObj = pathResultMap.get(python.getBuiltins().get("str").call("status"));

            if (pathStatusObj != null && "PATH_READY".equals(pathStatusObj.toString())) {
                isPathPlanned = true;
                PyObject firstInstruction = navigationProcessor.callAttr("_update_navigation_status", resultMap.get(python.getBuiltins().get("str").call("corners")));
                if (firstInstruction != null) {
                    handleNavigating(firstInstruction.asMap());
                }
            } else {
                PyObject errorObj = pathResultMap.get(python.getBuiltins().get("str").call("message"));
                String error = (errorObj != null) ? errorObj.toString() : "Path planner failed.";
                updateStatus("Error planning path: " + error, true);
            }
        } else {
            updateStatus("Location: " + locName, false);
        }
    }

    private void handleNavigating(Map<PyObject, PyObject> resultMap) {
        PyObject nextWpObj = resultMap.get(python.getBuiltins().get("str").call("next_waypoint_name"));
        PyObject azimuthObj = resultMap.get(python.getBuiltins().get("str").call("target_azimuth"));
        PyObject distanceObj = resultMap.get(python.getBuiltins().get("str").call("target_distance"));

        if (nextWpObj != null && azimuthObj != null && distanceObj != null) {
            String statusMessage = "Proceed to " + nextWpObj.toString();
            updateStatus(statusMessage, false);
            updateNavigationTarget(azimuthObj.toFloat(), distanceObj.toFloat());
        } else {
            updateStatus("Scan QR code to get next step.", true);
        }
    }

    private void updateStatus(String text, boolean speak) {
        statusText.setText(text);
        if (speak) {
            TTSService.getInstance().speak(text);
        }
    }

    private byte[] imageProxyToByteArray(ImageProxy image) {
        if (image.getFormat() != android.graphics.ImageFormat.YUV_420_888) {
            Log.e(TAG, "Unsupported image format: Not YUV_420_888");
            return null;
        }
        int width = image.getWidth();
        int height = image.getHeight();
        ImageProxy.PlaneProxy yPlane = image.getPlanes()[0];
        ImageProxy.PlaneProxy uPlane = image.getPlanes()[1];
        ImageProxy.PlaneProxy vPlane = image.getPlanes()[2];
        ByteBuffer yBuffer = yPlane.getBuffer();
        ByteBuffer uBuffer = uPlane.getBuffer();
        ByteBuffer vBuffer = vPlane.getBuffer();
        yBuffer.rewind();
        uBuffer.rewind();
        vBuffer.rewind();
        byte[] nv21 = new byte[width * height * 3 / 2];
        int yRowStride = yPlane.getRowStride();
        int yPixelStride = yPlane.getPixelStride();
        int yPos = 0;
        if (yPixelStride == 1 && yRowStride == width) {
            yBuffer.get(nv21, 0, width * height);
        } else {
            for (int row = 0; row < height; row++) {
                yBuffer.position(row * yRowStride);
                yBuffer.get(nv21, yPos, width);
                yPos += width;
            }
        }
        int uvRowStride = vPlane.getRowStride();
        int uvPixelStride = vPlane.getPixelStride();
        int vuPos = width * height;
        for (int row = 0; row < height / 2; row++) {
            for (int col = 0; col < width / 2; col++) {
                int vPos = row * uvRowStride + col * uvPixelStride;
                if (vPos < vBuffer.capacity()) {
                    nv21[vuPos++] = vBuffer.get(vPos);
                }
                if (vPos < uBuffer.capacity()) {
                    nv21[vuPos++] = uBuffer.get(vPos);
                }
            }
        }
        return nv21;
    }

    public void updateNavigationTarget(float newAzimuth, float newDistance) {
        this.targetAzimuth = newAzimuth;
        this.targetDistance = newDistance;
        updateDistanceUI(newDistance);
    }

    @Override
    protected void onResume() {
        super.onResume();
        Sensor accel = sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        if (accel != null) sensorManager.registerListener(this, accel, SensorManager.SENSOR_DELAY_GAME);
        Sensor mag = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD);
        if (mag != null) sensorManager.registerListener(this, mag, SensorManager.SENSOR_DELAY_GAME);
    }

    @Override
    protected void onPause() {
        super.onPause();
        sensorManager.unregisterListener(this);
    }

    @Override
    protected void onDestroy() {
        TTSService.getInstance().shutdown();
        super.onDestroy();
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        final float alpha = 0.97f;
        if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            gravity[0] = alpha * gravity[0] + (1 - alpha) * event.values[0];
            gravity[1] = alpha * gravity[1] + (1 - alpha) * event.values[1];
            gravity[2] = alpha * gravity[2] + (1 - alpha) * event.values[2];
        } else if (event.sensor.getType() == Sensor.TYPE_MAGNETIC_FIELD) {
            geomagnetic[0] = alpha * geomagnetic[0] + (1 - alpha) * event.values[0];
            geomagnetic[1] = alpha * geomagnetic[1] + (1 - alpha) * event.values[1];
            geomagnetic[2] = alpha * geomagnetic[2] + (1 - alpha) * event.values[2];
        }
        float[] R = new float[9], I = new float[9];
        if (SensorManager.getRotationMatrix(R, I, gravity, geomagnetic)) {
            float[] orientation = new float[3];
            SensorManager.getOrientation(R, orientation);
            float deviceAzimuth = (float) Math.toDegrees(orientation[0]);
            deviceAzimuth = (deviceAzimuth + 360) % 360;

            // MODIFIED: This is the core fix. Only give guidance if a path is planned AND we have not arrived.
            if (isPathPlanned && !hasArrived) {
                float angleToTarget = (targetAzimuth - deviceAzimuth + 360) % 360;
                rotateArrow(angleToTarget);
                provideDirectionalFeedback(angleToTarget);
            }
        }
    }

    private void rotateArrow(float angleToTarget) {
        RotateAnimation anim = new RotateAnimation(currentArrowRotation, angleToTarget,
                RotateAnimation.RELATIVE_TO_SELF, 0.5f,
                RotateAnimation.RELATIVE_TO_SELF, 0.5f);
        anim.setDuration(210);
        anim.setFillAfter(true);
        arrowImage.startAnimation(anim);
        currentArrowRotation = angleToTarget;
    }

    private void updateDistanceUI(float distanceMeters) {
        distanceText.setText(String.format(Locale.US, "%.1f m", distanceMeters));
    }

    private void provideDirectionalFeedback(float angleToTarget) {
        long now = System.currentTimeMillis();
        if (now - lastFeedbackTime < FEEDBACK_INTERVAL_MS) return;

        lastFeedbackTime = now;
        if (angleToTarget <= TOLERANCE_DEGREES || angleToTarget >= 360 - TOLERANCE_DEGREES) {
            if (vibrator != null) vibrator.vibrate(150);
            TTSService.getInstance().speak("Straight ahead.");
        } else {
            if (vibrator != null) vibrator.vibrate(new long[]{0, 200, 100, 200}, -1);
            if (angleToTarget > TOLERANCE_DEGREES && angleToTarget <= 180) {
                TTSService.getInstance().speak("Turn right");
            } else {
                TTSService.getInstance().speak("Turn left");
            }
        }
    }

    private boolean isCameraPermissionGranted() {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
    }

    private void requestCameraPermission() {
        ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.CAMERA}, CAMERA_PERMISSION_REQUEST_CODE);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_PERMISSION_REQUEST_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startCamera();
            } else {
                Toast.makeText(this, "Camera permission is required.", Toast.LENGTH_SHORT).show();
            }
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {}
}
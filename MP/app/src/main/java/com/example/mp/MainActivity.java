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

public class MainActivity extends AppCompatActivity implements SensorEventListener {

    private static final String TAG = "MainActivity";
    private static final int CAMERA_PERMISSION_REQUEST_CODE = 101;
    private static final float TOLERANCE_DEGREES = 10f;
    private static final long FEEDBACK_INTERVAL_MS = 750;
    private ImageView arrowImage;
    private TextView distanceText;
    private PreviewView cameraPreview;
    private SensorManager sensorManager;
    private Vibrator vibrator;
    private long lastFeedbackTime = 0L;
    private float currentArrowRotation = 0f;
    private final float[] gravity = new float[3];
    private final float[] geomagnetic = new float[3];
    private float targetAzimuth = 0.0f;
    private float targetDistance = 0.0f;
    private Python python;
    private PyObject navigationProcessor;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        arrowImage = findViewById(R.id.arrowImage);
        distanceText = findViewById(R.id.distanceText);
        cameraPreview = findViewById(R.id.cameraPreview);

        initPython();
        if (python != null) {
            navigationProcessor = python.getModule("navigation_logic").callAttr("NavigationProcessor");
            String destinationId = getIntent().getStringExtra("DESTINATION_ID");
            if (destinationId != null) {
                navigationProcessor.callAttr("set_destination", destinationId);
            } else {
                Log.e(TAG, "No destination ID was provided.");
                Toast.makeText(this, "Error: No destination selected.", Toast.LENGTH_LONG).show();
                finish();
                return;
            }
        }

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        vibrator = (Vibrator) getSystemService(VIBRATOR_SERVICE);

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

                imageAnalysis.setAnalyzer(ContextCompat.getMainExecutor(this), imageProxy -> {
                    byte[] imageData = imageProxyToByteArray(imageProxy);
                    if (imageData != null && navigationProcessor != null) {
                        PyObject result = navigationProcessor.callAttr("process_frame",
                                imageData, imageProxy.getWidth(), imageProxy.getHeight());
                        if (result != null) {
                            PyObject azimuthObj = result.get("target_azimuth");
                            PyObject distanceObj = result.get("target_distance");
                            if (azimuthObj != null && distanceObj != null) {
                                float targetAzimuth = azimuthObj.toFloat();
                                float targetDistance = distanceObj.toFloat();
                                if (targetAzimuth == -1.0) {
                                    TTSService.getInstance().speak("You have reached your destination.");
                                } else {
                                    updateNavigationTarget(targetAzimuth, targetDistance);
                                }
                            }
                        }
                    }
                    imageProxy.close();
                });

                cameraProvider.unbindAll();
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalysis);
            } catch (Exception e) {
                Log.e(TAG, "CameraX binding failed", e);
            }
        }, ContextCompat.getMainExecutor(this));
    }

    private byte[] imageProxyToByteArray(ImageProxy image) {
        if (image.getFormat() != android.graphics.ImageFormat.YUV_420_888) return null;
        ByteBuffer yBuffer = image.getPlanes()[0].getBuffer();
        ByteBuffer uBuffer = image.getPlanes()[1].getBuffer();
        ByteBuffer vBuffer = image.getPlanes()[2].getBuffer();
        int ySize = yBuffer.remaining();
        int uSize = uBuffer.remaining();
        int vSize = vBuffer.remaining();
        byte[] nv21 = new byte[ySize + uSize + vSize];
        yBuffer.get(nv21, 0, ySize);
        vBuffer.get(nv21, ySize, vSize);
        uBuffer.get(nv21, ySize + vSize, uSize);
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
        if (accel != null) {
            sensorManager.registerListener(this, accel, SensorManager.SENSOR_DELAY_GAME);
        }
        Sensor mag = sensorManager.getDefaultSensor(Sensor.TYPE_MAGNETIC_FIELD);
        if (mag != null) {
            sensorManager.registerListener(this, mag, SensorManager.SENSOR_DELAY_GAME);
        }
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
            float angleToTarget = (targetAzimuth - deviceAzimuth + 360) % 360;
            rotateArrow(angleToTarget);
            provideDirectionalFeedback(angleToTarget);
        }
    }

    private void rotateArrow(float angleToTarget) {
        RotateAnimation anim = new RotateAnimation(
                currentArrowRotation,
                angleToTarget,
                RotateAnimation.RELATIVE_TO_SELF, 0.5f,
                RotateAnimation.RELATIVE_TO_SELF, 0.5f
        );
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
        if (angleToTarget <= TOLERANCE_DEGREES || angleToTarget >= 360 - TOLERANCE_DEGREES) {
            lastFeedbackTime = now;
            handleOnTargetFeedback();
            return;
        }
        lastFeedbackTime = now;
        handleTurnFeedback(angleToTarget);
    }

    private void handleOnTargetFeedback() {
        if (vibrator != null) vibrator.vibrate(150);
        String message;
        if (targetDistance < 2.0f) message = "Just ahead.";
        else if (targetDistance < 5.0f) message = "Getting closer.";
        else message = "Straight ahead.";
        TTSService.getInstance().speak(message);
    }

    private void handleTurnFeedback(float angleToTarget) {
        if (vibrator != null) vibrator.vibrate(300);
        if (angleToTarget > TOLERANCE_DEGREES && angleToTarget <= 180) {
            TTSService.getInstance().speak("Turn right");
        } else {
            TTSService.getInstance().speak("Turn left");
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
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
        // Not used
    }
}
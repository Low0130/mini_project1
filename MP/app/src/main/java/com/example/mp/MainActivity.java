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
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.util.Log;
import android.view.animation.RotateAnimation;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.Preview;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import com.google.common.util.concurrent.ListenableFuture;
import java.util.Locale;
import java.util.concurrent.ExecutionException;

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
    private TextToSpeech tts;
    private volatile boolean ttsBusy = false;
    private long lastFeedbackTime = 0L;
    private float currentArrowRotation = 0f;
    private final float[] gravity = new float[3];
    private final float[] geomagnetic = new float[3];
    private float targetAzimuth = 0.0f;
    private float targetDistance = 0.0f;


    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        arrowImage = findViewById(R.id.arrowImage);
        distanceText = findViewById(R.id.distanceText);
        cameraPreview = findViewById(R.id.cameraPreview);

        sensorManager = (SensorManager) getSystemService(Context.SENSOR_SERVICE);
        vibrator = (Vibrator) getSystemService(VIBRATOR_SERVICE);
        initializeTTS();

        if (isCameraPermissionGranted()) {
            startCamera();
        } else {
            requestCameraPermission();
        }

        updateNavigationTarget(90.0f, 15.2f);
    }


    private void initializeTTS() {
        tts = new TextToSpeech(this, status -> {
            if (status == TextToSpeech.SUCCESS) {
                int langStatus = tts.setLanguage(Locale.US);
                if (langStatus == TextToSpeech.LANG_MISSING_DATA || langStatus == TextToSpeech.LANG_NOT_SUPPORTED) {
                    Log.w(TAG, "US-English TTS not supported.");
                    tts = null;
                } else {
                    tts.setSpeechRate(1.2f);
                    tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                        @Override public void onStart(String utteranceId) { ttsBusy = true; }
                        @Override public void onDone(String utteranceId) { ttsBusy = false; }
                        @Override public void onError(String utteranceId) { ttsBusy = false; }
                    });
                }
            } else {
                Log.w(TAG, "TTS initialization failed");
            }
        });
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
        if (tts != null) {
            tts.stop();
            tts.shutdown();
        }
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

        float[] R = new float[9];
        float[] I = new float[9];
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
        if (now - lastFeedbackTime < FEEDBACK_INTERVAL_MS) {
            return;
        }

        if (angleToTarget <= TOLERANCE_DEGREES || angleToTarget >= 360 - TOLERANCE_DEGREES) {
            lastFeedbackTime = now;
            handleOnTargetFeedback();
            return;
        }

        lastFeedbackTime = now;
        handleTurnFeedback(angleToTarget);
    }

    private void handleOnTargetFeedback() {
        if (vibrator != null) {
            vibrator.vibrate(150);
        }

        if (tts != null && !ttsBusy) {
            String message;
            if (targetDistance < 2.0f) {
                message = "Just ahead.";
            } else if (targetDistance < 5.0f) {
                message = "Getting closer.";
            } else {
                message = "Straight ahead.";
            }
            tts.speak(message, TextToSpeech.QUEUE_FLUSH, null, "ON_TARGET");
        }
    }

    private void handleTurnFeedback(float angleToTarget) {
        if (vibrator != null) {
            vibrator.vibrate(300);
        }

        if (tts != null && !ttsBusy) {
            if (angleToTarget > TOLERANCE_DEGREES && angleToTarget <= 180) {
                tts.speak("Turn left", TextToSpeech.QUEUE_FLUSH, null, "TURN_LEFT");
            } else {
                tts.speak("Turn right", TextToSpeech.QUEUE_FLUSH, null, "TURN_RIGHT");
            }
        }
    }

    private void startCamera() {
        ListenableFuture<ProcessCameraProvider> cameraProviderFuture = ProcessCameraProvider.getInstance(this);
        cameraProviderFuture.addListener(() -> {
            try {
                ProcessCameraProvider cameraProvider = cameraProviderFuture.get();
                Preview preview = new Preview.Builder().build();
                preview.setSurfaceProvider(cameraPreview.getSurfaceProvider());
                CameraSelector cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA;
                cameraProvider.unbindAll();
                cameraProvider.bindToLifecycle(this, cameraSelector, preview);
            } catch (ExecutionException | InterruptedException e) {
                Log.e(TAG, "CameraX binding failed", e);
            }
        }, ContextCompat.getMainExecutor(this));
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
    }
}
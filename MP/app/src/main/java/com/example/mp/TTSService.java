package com.example.mp;

import android.content.Context;
import android.speech.tts.TextToSpeech;
import android.util.Log;
import java.util.Locale;

// A Singleton class to manage TextToSpeech across the entire app
public class TTSService {

    private static final String TAG = "TTSService";
    private static TTSService instance;
    private TextToSpeech tts;
    private boolean isInitialized = false;

    private TTSService() {}

    public static synchronized TTSService getInstance() {
        if (instance == null) {
            instance = new TTSService();
        }
        return instance;
    }

    public void initialize(Context context) {
        if (isInitialized) {
            return;
        }
        tts = new TextToSpeech(context.getApplicationContext(), status -> {
            if (status == TextToSpeech.SUCCESS) {
                int langStatus = tts.setLanguage(Locale.US);
                if (langStatus == TextToSpeech.LANG_MISSING_DATA || langStatus == TextToSpeech.LANG_NOT_SUPPORTED) {
                    Log.e(TAG, "US-English TTS not supported.");
                } else {
                    isInitialized = true;
                    Log.i(TAG, "TTS initialized successfully.");
                }
            } else {
                Log.e(TAG, "TTS initialization failed.");
            }
        });
    }

    public void speak(String text) {
        speak(text, TextToSpeech.QUEUE_FLUSH); // Default to flushing the queue
    }

    public void speak(String text, int queueMode) {
        if (!isInitialized || tts == null) {
            Log.e(TAG, "TTS not initialized, cannot speak.");
            return;
        }
        tts.speak(text, queueMode, null, null);
    }

    public void shutdown() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
            isInitialized = false;
        }
        instance = null; // Clear the instance for a full reset if needed
    }
}
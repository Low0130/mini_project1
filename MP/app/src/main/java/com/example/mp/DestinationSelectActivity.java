// DestinationSelectActivity.java

package com.example.mp;

import android.content.Intent;
import android.os.Bundle;
import android.speech.tts.TextToSpeech; // <--- ADD THIS IMPORT
import android.util.Log;
import android.util.Pair;
import android.view.GestureDetector;
import android.view.MotionEvent;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.view.GestureDetectorCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class DestinationSelectActivity extends AppCompatActivity {

    private static final String TAG = "DestinationSelect";
    private RecyclerView recyclerView;
    private DestinationAdapter adapter;
    private final List<Pair<String, String>> destinations = new ArrayList<>();
    private GestureDetectorCompat gestureDetector;
    private Python python;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_destination_select);

        recyclerView = findViewById(R.id.recyclerViewDestinations);
        recyclerView.setLayoutManager(new LinearLayoutManager(this));

        gestureDetector = new GestureDetectorCompat(this, new RecyclerViewGestureListener());

        recyclerView.addOnItemTouchListener(new RecyclerView.OnItemTouchListener() {
            @Override
            public boolean onInterceptTouchEvent(@NonNull RecyclerView rv, @NonNull MotionEvent e) {
                gestureDetector.onTouchEvent(e);
                return false;
            }
            @Override
            public void onTouchEvent(@NonNull RecyclerView rv, @NonNull MotionEvent e) {}
            @Override
            public void onRequestDisallowInterceptTouchEvent(boolean disallowIntercept) {}
        });

        initPython();
        loadDestinations();

        // MODIFIED: We now explicitly tell the first message to FLUSH the queue.
        TTSService.getInstance().speak("Select a destination by swiping up or down. Tap to confirm.", TextToSpeech.QUEUE_FLUSH);
    }

    private void initPython() {
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
        python = Python.getInstance();
    }

    private void loadDestinations() {
        Log.d(TAG, "Attempting to load destinations from Python...");
        try {
            PyObject navigationProcessor = python.getModule("navigation_logic").callAttr("NavigationProcessor");
            PyObject locationsResult = navigationProcessor.callAttr("get_all_locations");

            if (locationsResult == null) {
                Log.e(TAG, "Python call to get_all_locations returned null!");
                return;
            }

            Map<PyObject, PyObject> locationsMap = locationsResult.asMap();
            PyObject locationsListPy = locationsMap.get(python.getBuiltins().get("str").call("locations"));

            if (locationsListPy != null) {
                List<PyObject> pyDestinations = locationsListPy.asList();
                Log.i(TAG, "Successfully extracted " + pyDestinations.size() + " destinations from the list.");

                for (PyObject dest : pyDestinations) {
                    Map<PyObject, PyObject> destMap = dest.asMap();
                    PyObject idObj = destMap.get(python.getBuiltins().get("str").call("location_id"));
                    PyObject nameObj = destMap.get(python.getBuiltins().get("str").call("location_name"));

                    if (idObj != null && nameObj != null) {
                        destinations.add(new Pair<>(idObj.toString(), nameObj.toString()));
                    } else {
                        Log.w(TAG, "Skipping a destination due to missing 'location_id' or 'location_name'.");
                    }
                }
            } else {
                Log.e(TAG, "The 'locations' key was not found in the converted Python result map.");
            }
        } catch (Exception e) {
            Log.e(TAG, "An error occurred while loading destinations", e);
            TTSService.getInstance().speak("A critical error occurred while loading destinations.");
        }

        adapter = new DestinationAdapter(destinations);
        recyclerView.setAdapter(adapter);

        if (!destinations.isEmpty()) {
            // MODIFIED: We now call a special version of announceSelection for the initial announcement.
            recyclerView.postDelayed(() -> announceInitialSelection(adapter.getSelectedPosition()), 500); // Increased delay slightly
        } else {
            Log.e(TAG, "Destination list is empty after processing. Nothing to show.");
            TTSService.getInstance().speak("Error: Could not load any destinations.");
        }
    }

    // ADDED: A new method specifically for the first announcement that ADDS to the queue.
    private void announceInitialSelection(int index) {
        if (index >= 0 && index < destinations.size()) {
            String locationName = destinations.get(index).second;
            // This will wait for the "Select a destination..." message to finish.
            TTSService.getInstance().speak(locationName + ". Tap to confirm destination.", TextToSpeech.QUEUE_ADD);
        }
    }

    // MODIFIED: This method is now used for swipes. It FLUSHES the queue to be responsive.
    private void announceSwipeSelection(int index) {
        if (index >= 0 && index < destinations.size()) {
            String locationName = destinations.get(index).second;
            // This will interrupt any previous announcement to say the new selection immediately.
            TTSService.getInstance().speak(locationName, TextToSpeech.QUEUE_FLUSH);
        }
    }

    private void confirmSelection(int index) {
        if (index >= 0 && index < destinations.size()) {
            Pair<String, String> selected = destinations.get(index);
            String locationId = selected.first;
            String locationName = selected.second;
            TTSService.getInstance().speak("Destination set to " + locationName + ". Starting camera.");
            Intent intent = new Intent(DestinationSelectActivity.this, MainActivity.class);
            intent.putExtra("DESTINATION_ID", locationId);
            startActivity(intent);
            finish();
        }
    }

    private class RecyclerViewGestureListener extends GestureDetector.SimpleOnGestureListener {
        private static final int SWIPE_THRESHOLD = 100;
        private static final int SWIPE_VELOCITY_THRESHOLD = 100;

        @Override
        public boolean onSingleTapUp(MotionEvent e) {
            confirmSelection(adapter.getSelectedPosition());
            return true;
        }

        @Override
        public boolean onFling(@NonNull MotionEvent e1, @NonNull MotionEvent e2, float velocityX, float velocityY) {
            float diffY = e2.getY() - e1.getY();

            if (Math.abs(diffY) > SWIPE_THRESHOLD && Math.abs(velocityY) > SWIPE_VELOCITY_THRESHOLD) {
                int currentPosition = adapter.getSelectedPosition();
                int newPosition;

                if (diffY > 0) { // Swipe Down
                    newPosition = Math.max(0, currentPosition - 1);
                } else { // Swipe Up
                    newPosition = Math.min(destinations.size() - 1, currentPosition + 1);
                }

                if (newPosition != currentPosition) {
                    adapter.setSelectedPosition(newPosition);
                    recyclerView.smoothScrollToPosition(newPosition);
                    // MODIFIED: Call the swipe-specific announcement method.
                    announceSwipeSelection(newPosition);
                }
                return true;
            }
            return false;
        }
    }
}
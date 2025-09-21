package com.example.mp;

import android.content.Intent;
import android.os.Bundle;
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
    private List<Pair<String, String>> destinations = new ArrayList<>();
    private GestureDetectorCompat gestureDetector;

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

        TTSService.getInstance().speak("Select a destination.");
    }

    private void initPython() {
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
    }

    private void loadDestinations() {
        Python python = Python.getInstance();
        PyObject navigationProcessor = python.getModule("navigation_logic").callAttr("NavigationProcessor");
        PyObject locationsMap = navigationProcessor.callAttr("get_all_locations");

        if (locationsMap != null) {
            for (Map.Entry<PyObject, PyObject> entry : locationsMap.asMap().entrySet()) {
                destinations.add(new Pair<>(entry.getKey().toString(), entry.getValue().toString()));
            }
        } else {
            Log.e(TAG, "Failed to get locations from Python");
        }

        adapter = new DestinationAdapter(destinations);
        recyclerView.setAdapter(adapter);

        if (!destinations.isEmpty()) {
            recyclerView.postDelayed(() -> announceSelection(adapter.getSelectedPosition()), 250);
        }
    }

    private void announceSelection(int index) {
        if (index >= 0 && index < destinations.size()) {
            String locationName = destinations.get(index).second;
            TTSService.getInstance().speak(locationName + ". Tap to confirm destination.");
        }
    }

    private void confirmSelection(int index) {
        if (index >= 0 && index < destinations.size()) {
            Pair<String, String> selected = destinations.get(index);
            String locationId = selected.first;
            String locationName = selected.second;

            TTSService.getInstance().speak("Destination set to " + locationName + ". Please find and scan the nearest QR code to begin.");

            Intent intent = new Intent(DestinationSelectActivity.this, MainActivity.class);
            intent.putExtra("DESTINATION_ID", locationId);
            startActivity(intent);
        }
    }

    // This inner class handles the swipe and tap gestures
    private class RecyclerViewGestureListener extends GestureDetector.SimpleOnGestureListener {
        private static final int SWIPE_THRESHOLD = 100;
        private static final int SWIPE_VELOCITY_THRESHOLD = 100;

        @Override
        public boolean onSingleTapUp(MotionEvent e) {
            confirmSelection(adapter.getSelectedPosition());
            return true;
        }

        @Override
        public boolean onFling(MotionEvent e1, MotionEvent e2, float velocityX, float velocityY) {
            float diffY = e2.getY() - e1.getY();

            if (Math.abs(diffY) > SWIPE_THRESHOLD && Math.abs(velocityY) > SWIPE_VELOCITY_THRESHOLD) {
                int currentPosition = adapter.getSelectedPosition();
                if (diffY > 0) {
                    // Swipe Down - move to PREVIOUS item
                    int newPosition = Math.max(0, currentPosition - 1);
                    if (newPosition != currentPosition) {
                        adapter.setSelectedPosition(newPosition);
                        // **THIS IS THE FIX: Tell the RecyclerView to scroll**
                        recyclerView.smoothScrollToPosition(newPosition);
                        announceSelection(newPosition);
                    }
                } else {
                    // Swipe Up - move to NEXT item
                    int newPosition = Math.min(destinations.size() - 1, currentPosition + 1);
                    if (newPosition != currentPosition) {
                        adapter.setSelectedPosition(newPosition);
                        // **THIS IS THE FIX: Tell the RecyclerView to scroll**
                        recyclerView.smoothScrollToPosition(newPosition);
                        announceSelection(newPosition);
                    }
                }
                return true;
            }
            return false;
        }
    }
}
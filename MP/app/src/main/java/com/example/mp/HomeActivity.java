package com.example.mp;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.RelativeLayout;
import androidx.appcompat.app.AppCompatActivity;

public class HomeActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_home);

        // Initialize our central TTS service
        TTSService.getInstance().initialize(getApplicationContext());

        RelativeLayout homeLayout = findViewById(R.id.homeLayout);

        // Speak the welcome message after a short delay to ensure TTS is ready
        homeLayout.postDelayed(() -> {
            TTSService.getInstance().speak("Welcome to Block N Navigator. Tap anywhere to select a destination.");
        }, 1000); // 1000ms delay

        homeLayout.setOnClickListener(v -> {
            Intent intent = new Intent(HomeActivity.this, DestinationSelectActivity.class);
            startActivity(intent);
        });
    }
}
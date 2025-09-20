plugins {
    alias(libs.plugins.android.application)
    id("com.chaquo.python")
}

android {
    namespace = "com.example.mp"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.example.mp"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk {
            abiFilters.addAll(listOf("arm64-v8a", "x86_64"))
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}

// THIS IS THE FINAL, SIMPLE, AND CORRECT SYNTAX
chaquopy {
    defaultConfig {
        version = "3.10"
        pip {
            install("numpy")
            install("opencv-python @ https://chaquo.com/pypi-13.1/opencv-python/opencv_python-4.6.0.66-5-cp310-cp310-android_21_arm64_v8a.whl")
            install("src/main/python/libs/pyzbar-0.1.9-py2.py3-none-any.whl")
        }
    }
}

dependencies {
    implementation(libs.camera.core)
    implementation(libs.camera.camera2)
    implementation(libs.camera.lifecycle)
    implementation(libs.camera.view)
    implementation(libs.appcompat)
    implementation(libs.material)
    implementation(libs.activity)
    implementation(libs.constraintlayout)
    testImplementation(libs.junit)
    androidTestImplementation(libs.ext.junit)
    androidTestImplementation(libs.espresso.core)
}
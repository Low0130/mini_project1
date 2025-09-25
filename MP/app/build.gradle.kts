plugins {
    alias(libs.plugins.android.application)
    id("com.chaquo.python")
}

android {
    namespace = "com.example.mp"
    compileSdk = 36
    flavorDimensions += "pyVersion"
    productFlavors {
        create("py38") { dimension = "pyVersion" }

    }

    defaultConfig {
        applicationId = "com.example.mp"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
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

// THIS IS THE CORRECT, ROBUST SYNTAX FOR MODERN KOTLIN DSL
chaquopy{

    productFlavors {
        getByName("py38") { version = "3.8" }

    }
    defaultConfig{
        pip {
            install("numpy")

            install("opencv-python")

            install("pyzbar")

            install("matplotlib")
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
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.videodownloader.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.videodownloader.app"
        minSdk = 24
        targetSdk = 34
        // CI passes the run number so every new build installs over the old one.
        versionCode = (System.getenv("VERSION_CODE") ?: "1").toInt()
        versionName = "1.0"
    }

    signingConfigs {
        // Same shared debug key as the game, so updates install without uninstalling.
        getByName("debug") {
            storeFile = rootProject.file("../../tools/debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
    // Android's own org.json is only a stub in unit tests; the queue file is JSON.
    testImplementation("org.json:json:20240303")
}

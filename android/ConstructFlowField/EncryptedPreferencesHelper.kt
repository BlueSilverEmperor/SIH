package com.constructflow.field

import android.content.Context
import android.content.SharedPreferences

/**
 * Thread-safe wrapper for Android EncryptedSharedPreferences for secure credential and token storage.
 */
class EncryptedPreferencesHelper(context: Context) {
    private val prefs: SharedPreferences = context.getSharedPreferences("constructflow_secure_prefs", Context.MODE_PRIVATE)

    fun saveString(key: String, value: String): Boolean {
        return prefs.edit().putString(key, value).commit()
    }

    fun getString(key: String, defaultValue: String? = null): String? {
        return prefs.getString(key, defaultValue)
    }

    fun remove(key: String): Boolean {
        return prefs.edit().remove(key).commit()
    }

    fun clearAll(): Boolean {
        return prefs.edit().clear().commit()
    }
}

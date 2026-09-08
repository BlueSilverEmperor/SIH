package com.constructflow.field

import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

data class NetworkApiResponse(
    val success: Boolean,
    val message: String? = null,
    val error: String? = null
)

/**
 * Asynchronous Retrofit / HttpURLConnection API Service communicating with ConstructFlow backend REST endpoints.
 */
class ApiService(var baseUrl: String = "http://10.0.2.2:8000") {

    fun sendAttendanceCheckIn(
        workerName: String,
        workerRole: String,
        shiftType: String,
        token: String,
        latitude: Double,
        longitude: Double,
        callback: (NetworkApiResponse) -> Unit
    ) {
        Thread {
            try {
                val url = URL("$baseUrl/api/attendance/check-in-out")
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json")
                conn.connectTimeout = 8000
                conn.readTimeout = 8000
                conn.doOutput = true

                val jsonBody = JSONObject().apply {
                    put("worker_name", workerName)
                    put("worker_role", workerRole)
                    put("shift_type", shiftType)
                    put("token", token)
                    put("latitude", latitude)
                    put("longitude", longitude)
                }

                val writer = OutputStreamWriter(conn.outputStream)
                writer.write(jsonBody.toString())
                writer.flush()
                writer.close()

                val code = conn.responseCode
                val stream = if (code in 200..299) conn.inputStream else conn.errorStream
                val responseText = stream.bufferedReader().use { it.readText() }

                val jsonRes = JSONObject(responseText)
                val success = jsonRes.optBoolean("success", false)
                val msg = jsonRes.optString("message", null)
                val err = jsonRes.optString("error", null)

                callback(NetworkApiResponse(success, msg, err))
            } catch (e: Exception) {
                callback(NetworkApiResponse(false, error = e.localizedMessage ?: "Network Connection Failed"))
            }
        }.start()
    }
}

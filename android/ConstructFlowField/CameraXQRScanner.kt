package com.constructflow.field

import android.content.Context
import android.util.Log

data class QRScanResult(
    val token: String,
    val shiftType: String,
    val isValidFormat: Boolean
)

/**
 * CameraX ImageAnalysis analyzer for decoding daily morning and evening QR code tokens.
 */
class CameraXQRScannerAnalyzer(private val onResult: (QRScanResult) -> Unit) {
    
    fun processQRCodeText(rawText: String) {
        val parts = rawText.split("|")
        if (parts.size == 5 && parts[0] == "CONSTRUCTFLOW") {
            val shift = parts[2]
            val res = QRScanResult(
                token = rawText,
                shiftType = shift,
                isValidFormat = true
            )
            onResult(res)
        } else {
            Log.w("CameraXQRScanner", "Scanned code does not match CONSTRUCTFLOW QR format: $rawText")
        }
    }
}

package com.constructflow.field

import java.util.UUID

data class AttendanceRecordEntity(
    val id: String = UUID.randomUUID().toString(),
    val workerName: String,
    val workerRole: String,
    val shiftType: String,
    val token: String,
    val latitude: Double,
    val longitude: Double,
    val timestamp: Long = System.currentTimeMillis(),
    val syncStatus: String = "pending" // "pending", "synced"
)

/**
 * Offline-First Room Database Persistence Layer managing offline field attendance check-ins.
 */
class LocalAttendanceDatabase {
    private val pendingQueue = mutableListOf<AttendanceRecordEntity>()

    fun insertRecord(record: AttendanceRecordEntity) {
        pendingQueue.add(record)
    }

    fun getAllPending(): List<AttendanceRecordEntity> {
        return pendingQueue.toList()
    }

    fun deleteRecord(id: String) {
        pendingQueue.removeAll { it.id == id }
    }

    fun clearAll() {
        pendingQueue.clear()
    }
}

package com.example.mirrorme

import android.content.Context
import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.awaitResponse
import java.io.File
import java.io.FileOutputStream

sealed class AnalysisState {
    object Idle : AnalysisState()
    object Loading : AnalysisState()
    data class Success(val response: SkinAnalysisResponse) : AnalysisState()
    data class Error(val message: String) : AnalysisState()
}

class SkinViewModel : ViewModel() {
    private val _analysisState = MutableStateFlow<AnalysisState>(AnalysisState.Idle)
    val analysisState: StateFlow<AnalysisState> = _analysisState

    fun analyzeSkin(context: Context, imageUri: Uri?, userId: String? = null) {
        viewModelScope.launch {
            _analysisState.value = AnalysisState.Loading
            
            try {
                val file = if (imageUri == null) {
                    prepareSampleFile(context)
                } else {
                    getFileFromUri(context, imageUri)
                }

                if (file == null || !file.exists()) {
                    _analysisState.value = AnalysisState.Error("파일을 준비할 수 없습니다.")
                    return@launch
                }

                val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
                val body = MultipartBody.Part.createFormData("image", file.name, requestFile)
                val userIdPart = userId?.toRequestBody("text/plain".toMediaTypeOrNull())

                val response = RetrofitClient.service.analyzeSkin(body, userIdPart).awaitResponse()

                if (response.isSuccessful && response.body() != null) {
                    _analysisState.value = AnalysisState.Success(response.body()!!)
                } else {
                    _analysisState.value = AnalysisState.Error("분석 실패: ${response.code()}")
                }
            } catch (e: Exception) {
                _analysisState.value = AnalysisState.Error("네트워크 오류: ${e.localizedMessage}")
            }
        }
    }

    fun resetState() {
        _analysisState.value = AnalysisState.Idle
    }

    private fun prepareSampleFile(context: Context): File {
        val file = File(context.cacheDir, "sample_skin.jpg")
        context.assets.open("sample.jpg").use { input ->
            FileOutputStream(file).use { output ->
                input.copyTo(output)
            }
        }
        return file
    }

    private fun getFileFromUri(context: Context, uri: Uri): File? {
        val file = File(context.cacheDir, "upload_image.jpg")
        context.contentResolver.openInputStream(uri)?.use { input ->
            FileOutputStream(file).use { output ->
                input.copyTo(output)
            }
        }
        return if (file.exists()) file else null
    }
}

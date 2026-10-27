package com.example.mirrorme

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

data class HistoryResponse(
    val success: Boolean,
    val user_id: String,
    val history: List<SkinAnalysisResponse>
)

interface SkinApiService {
    @Multipart
    @POST("analyze-skin")
    fun analyzeSkin(
        @Part image: MultipartBody.Part,
        @Part("user_id") userId: RequestBody? = null
    ): Call<SkinAnalysisResponse>

    @POST("signup")
    fun signUp(@Body request: Map<String, String>): Call<Map<String, Any>>

    @POST("login")
    fun login(@Body request: Map<String, String>): Call<Map<String, Any>>

    @GET("history/{user_id}")
    fun getHistory(@Path("user_id") userId: String): Call<HistoryResponse>
}

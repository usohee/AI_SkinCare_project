package com.example.mirrorme

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Call
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

interface SkinApiService {
    @Multipart
    @POST("analyze-skin")
    fun analyzeSkin(
        @Part image: MultipartBody.Part,
        @Part("user_id") userId: RequestBody? = null
    ): Call<SkinAnalysisResponse>
}

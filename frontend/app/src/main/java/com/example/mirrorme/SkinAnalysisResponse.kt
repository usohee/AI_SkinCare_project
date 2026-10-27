package com.example.mirrorme

import com.google.gson.annotations.SerializedName
import java.io.Serializable

data class SkinAnalysisResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("user_id") val userId: String? = null,
    @SerializedName("date") val date: String? = null, // 분석 날짜 필드 추가
    @SerializedName("total_score") val totalScore: Int,
    @SerializedName("scores") val scores: SkinDetails,
    @SerializedName("raw_values") val rawValues: Map<String, Any>? = null,
    @SerializedName("llm_report") val llmReport: String? = null,
    @SerializedName("recommendations") val recommendations: List<Recommendation>? = null
) : Serializable

data class SkinDetails(
    @SerializedName("acne") val acne: Int,
    @SerializedName("pigmentation") val pigmentation: Int,
    @SerializedName("pore") val pore: Int,
    @SerializedName("sebum") val sebum: Int
) : Serializable

data class Recommendation(
    @SerializedName("name") val name: String,
    @SerializedName("brand") val brand: String,
    @SerializedName("image_url") val imageUrl: String? = null
) : Serializable

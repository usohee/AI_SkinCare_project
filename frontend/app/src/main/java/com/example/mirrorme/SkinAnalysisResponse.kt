package com.example.mirrorme

import com.google.gson.annotations.SerializedName

data class SkinAnalysisResponse(
    @SerializedName("success") val success: Boolean,
    @SerializedName("user_id") val userId: String? = null,
    @SerializedName("total_score") val totalScore: Int,
    @SerializedName("scores") val scores: SkinDetails,
    @SerializedName("raw_values") val rawValues: Map<String, Any>? = null,
    @SerializedName("llm_report") val llmReport: LlmReport? = null
)

data class SkinDetails(
    @SerializedName("acne") val acne: Int,
    @SerializedName("pigmentation") val pigmentation: Int,
    @SerializedName("pore") val pore: Int,
    @SerializedName("sebum") val sebum: Int
)

data class LlmReport(
    @SerializedName("summary") val summary: String,
    @SerializedName("indicators") val indicators: Map<String, String>,
    @SerializedName("care_tip_ids") val careTipIds: List<String>
)

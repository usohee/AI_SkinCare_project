package com.example.mirrorme

import androidx.activity.viewModels
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import com.example.mirrorme.ui.theme.MirrorMeTheme

sealed interface Screen {
    object Analysis : Screen
    data class Report(val response: SkinAnalysisResponse) : Screen
}

class MainActivity : ComponentActivity() {
    private val viewModel: SkinViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MirrorMeTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    var currentScreen by remember { mutableStateOf<Screen>(Screen.Analysis) }

                    when (val screen = currentScreen) {
                        is Screen.Analysis -> {
                            AnalysisScreen(
                                viewModel = viewModel,
                                onNavigateToResult = { response ->
                                    currentScreen = Screen.Report(response)
                                },
                                onNavigateToHistory = { date ->
                                    // 해당 날짜에 맞는 더미 데이터 생성하여 ReportScreen으로 이동
                                    val dummyResponse = SkinAnalysisResponse(
                                        success = true,
                                        totalScore = when(date) {
                                            "2024-04-27" -> 78
                                            "2024-04-11" -> 72
                                            "2024-03-15" -> 65
                                            else -> 60
                                        },
                                        scores = SkinDetails(acne = 75, pigmentation = 60, pore = 70, sebum = 55),
                                        llmReport = LlmReport(
                                            summary = "과거 기록($date)에 따른 피부 상태 리포트입니다. 전반적으로 양호한 상태를 유지하고 있습니다.",
                                            indicators = emptyMap(),
                                            careTipIds = emptyList()
                                        )
                                    )
                                    currentScreen = Screen.Report(dummyResponse)
                                }
                            )
                        }
                        is Screen.Report -> {
                            ReportScreen(
                                response = screen.response,
                                onBackClick = {
                                    currentScreen = Screen.Analysis
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}

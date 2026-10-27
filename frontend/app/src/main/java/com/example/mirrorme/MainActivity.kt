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
    object Login : Screen
    object SignUp : Screen
    object Analysis : Screen
    data class Report(val response: SkinAnalysisResponse) : Screen
}

class MainActivity : ComponentActivity() {
    private val viewModel: SkinViewModel by viewModels()
    private var loggedInUserId: String? = null
    private var loggedInNickname: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MirrorMeTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    var currentScreen by remember { mutableStateOf<Screen>(Screen.Login) }

                    when (val screen = currentScreen) {
                        is Screen.Login -> {
                            LoginScreen(
                                onLoginClick = { userId, nickname ->
                                    loggedInUserId = userId
                                    loggedInNickname = nickname
                                    viewModel.fetchHistory(userId) // 서버에서 해당 사용자의 히스토리 가져오기
                                    currentScreen = Screen.Analysis 
                                },
                                onSignUpClick = { currentScreen = Screen.SignUp }
                            )
                        }
                        is Screen.SignUp -> {
                            SignUpScreen(
                                onBackToLogin = { currentScreen = Screen.Login },
                                onSignUpComplete = { userId, nickname ->
                                    loggedInUserId = userId
                                    loggedInNickname = nickname
                                    viewModel.clearHistory() // 신규 사용자는 히스토리 비움
                                    currentScreen = Screen.Analysis 
                                }
                            )
                        }
                        is Screen.Analysis -> {
                            AnalysisScreen(
                                viewModel = viewModel,
                                userId = loggedInUserId,
                                onNavigateToResult = { response ->
                                    currentScreen = Screen.Report(response)
                                },
                                onNavigateToHistory = { response ->
                                    currentScreen = Screen.Report(response)
                                },
                                onLogout = {
                                    viewModel.logout() // ViewModel 상태 초기화
                                    loggedInUserId = null
                                    loggedInNickname = null
                                    currentScreen = Screen.Login
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

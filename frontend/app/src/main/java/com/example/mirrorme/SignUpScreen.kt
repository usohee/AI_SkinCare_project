package com.example.mirrorme

import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mirrorme.ui.theme.MirrorMeTheme
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SignUpScreen(
    onBackToLogin: () -> Unit = {},
    onSignUpComplete: (String, String) -> Unit = { _, _ -> }
) {
    var name by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    val context = LocalContext.current

    Scaffold(
        topBar = {
            TopAppBar(
                title = {},
                navigationIcon = {
                    IconButton(onClick = onBackToLogin) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.Black
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color.White)
                .padding(horizontal = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(20.dp))

            // 로고
            Image(
                painter = painterResource(id = R.drawable.mirrorme_logo_header),
                contentDescription = "MirrorMe Logo",
                modifier = Modifier.height(40.dp),
                contentScale = ContentScale.Fit
            )

            Spacer(modifier = Modifier.height(40.dp))

            Text(
                text = "회원가입",
                fontFamily = MM_Font,
                fontSize = 24.sp,
                fontWeight = FontWeight.Bold,
                color = Color.Black
            )

            Spacer(modifier = Modifier.height(32.dp))

            // 이름 입력
            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("이름", fontFamily = MM_Font) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(8.dp),
                singleLine = true
            )

            Spacer(modifier = Modifier.height(16.dp))

            // 이메일 입력
            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("이메일", fontFamily = MM_Font) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(8.dp),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email)
            )

            Spacer(modifier = Modifier.height(16.dp))

            // 비밀번호 입력
            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text("비밀번호", fontFamily = MM_Font) },
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(8.dp),
                visualTransformation = PasswordVisualTransformation(),
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password)
            )

            Spacer(modifier = Modifier.height(40.dp))

            // 가입하기 버튼
            Button(
                onClick = {
                    if (name.isBlank() || email.isBlank() || password.isBlank()) {
                        Toast.makeText(context, "모든 필드를 입력해주세요.", Toast.LENGTH_SHORT).show()
                        return@Button
                    }
                    isLoading = true
                    val signUpData = mapOf(
                        "nickname" to name,
                        "email" to email,
                        "password" to password
                    )
                    RetrofitClient.service.signUp(signUpData).enqueue(object : Callback<Map<String, Any>> {
                        override fun onResponse(call: Call<Map<String, Any>>, response: Response<Map<String, Any>>) {
                            isLoading = false
                            if (response.isSuccessful && response.body()?.get("success") == true) {
                                Toast.makeText(context, "회원가입 성공!", Toast.LENGTH_SHORT).show()
                                val userId = response.body()?.get("user_id") as? String ?: ""
                                onSignUpComplete(userId, name)
                            } else {
                                val message = response.body()?.get("message") as? String ?: "회원가입 실패"
                                Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
                            }
                        }

                        override fun onFailure(call: Call<Map<String, Any>>, t: Throwable) {
                            isLoading = false
                            Toast.makeText(context, "네트워크 오류: ${t.localizedMessage}", Toast.LENGTH_SHORT).show()
                        }
                    })
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(56.dp),
                enabled = !isLoading,
                colors = ButtonDefaults.buttonColors(containerColor = Color.Black),
                shape = RoundedCornerShape(8.dp)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
                } else {
                    Text(
                        text = "가입하기",
                        fontFamily = MM_Font,
                        color = Color.White,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
fun SignUpScreenPreview() {
    MirrorMeTheme {
        SignUpScreen()
    }
}
